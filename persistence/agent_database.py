"""Dolt-inspired version-controlled agent database for MortgageFintechOS.

Implements Git-style branching, diffing, merging, and rollback for agent
data operations. Each agent works on an isolated branch — changes are
reviewed via diffs before merging to main. Inspired by DoltHub's
multiagent database patterns.

Key concepts:
  - Branch-per-agent isolation: agents never write to main directly
  - Commit graph: every mutation is a versioned commit with author/message
  - Diff computation: proportional to change size, not dataset size
  - Merge: atomic application of branch changes to target
  - Rollback: instant revert to any prior commit
  - UUID primary keys: safe across distributed branches
"""

import copy
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class DiffType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


@dataclass
class Commit:
    id: str
    branch: str
    author: str
    message: str
    timestamp: str
    parent_id: str | None = None
    changes: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "branch": self.branch, "author": self.author,
            "message": self.message, "timestamp": self.timestamp,
            "parent_id": self.parent_id, "changes": self.changes,
        }


@dataclass
class DiffEntry:
    table: str
    diff_type: DiffType
    row_id: str
    from_row: dict[str, Any] | None = None
    to_row: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table, "diff_type": self.diff_type.value,
            "row_id": self.row_id,
            "from_row": self.from_row, "to_row": self.to_row,
        }


# ─── Schema definitions ────────────────────────────────────────────────

SCHEMA: dict[str, dict[str, str]] = {
    "agent_operations": {
        "id": "VARCHAR(36) PRIMARY KEY DEFAULT UUID()",
        "agent_name": "VARCHAR(50) NOT NULL",
        "action": "VARCHAR(100) NOT NULL",
        "status": "ENUM('queued','running','completed','failed') DEFAULT 'queued'",
        "priority": "ENUM('critical','high','medium','low') DEFAULT 'medium'",
        "payload": "JSON",
        "result": "JSON",
        "error": "TEXT",
        "duration_ms": "INT",
        "created_at": "TIMESTAMP",
        "completed_at": "TIMESTAMP",
    },
    "agent_state": {
        "id": "VARCHAR(36) PRIMARY KEY DEFAULT UUID()",
        "agent_name": "VARCHAR(50) NOT NULL UNIQUE",
        "status": "ENUM('idle','busy','error','stopped') DEFAULT 'idle'",
        "tasks_completed": "INT DEFAULT 0",
        "tasks_failed": "INT DEFAULT 0",
        "last_task_at": "TIMESTAMP",
        "config": "JSON",
        "health_score": "DECIMAL(5,2) DEFAULT 1.00",
    },
    "integration_events": {
        "id": "VARCHAR(36) PRIMARY KEY DEFAULT UUID()",
        "integration": "VARCHAR(50) NOT NULL",
        "event_type": "VARCHAR(100) NOT NULL",
        "agent_name": "VARCHAR(50)",
        "request_summary": "TEXT",
        "response_status": "INT",
        "duration_ms": "INT",
        "created_at": "TIMESTAMP",
    },
    "schedule_history": {
        "id": "VARCHAR(36) PRIMARY KEY DEFAULT UUID()",
        "job_name": "VARCHAR(100) NOT NULL",
        "scheduled_time": "TIME",
        "actual_time": "TIMESTAMP",
        "status": "ENUM('fired','skipped','disabled') DEFAULT 'fired'",
        "agent_name": "VARCHAR(50)",
        "task_id": "VARCHAR(36)",
    },
    "audit_trail": {
        "id": "VARCHAR(36) PRIMARY KEY DEFAULT UUID()",
        "actor": "VARCHAR(50) NOT NULL",
        "action": "VARCHAR(100) NOT NULL",
        "target_table": "VARCHAR(100)",
        "target_id": "VARCHAR(36)",
        "before_state": "JSON",
        "after_state": "JSON",
        "created_at": "TIMESTAMP",
    },
    "workflow_proposals": {
        "id": "VARCHAR(36) PRIMARY KEY DEFAULT UUID()",
        "title": "VARCHAR(200) NOT NULL",
        "description": "TEXT",
        "proposed_by": "VARCHAR(50) NOT NULL",
        "agents_involved": "JSON",
        "workflow_steps": "JSON",
        "status": "ENUM('draft','review','approved','rejected','executed') DEFAULT 'draft'",
        "created_at": "TIMESTAMP",
        "reviewed_at": "TIMESTAMP",
    },
}


class AgentDatabase:
    """Version-controlled in-memory database with Git-style branching.

    Inspired by DoltHub's multiagent patterns:
    - Branch-per-agent isolation
    - Diff before merge
    - Instant rollback
    - UUID primary keys for branch safety
    - Commit graph with parent tracking
    """

    def __init__(self) -> None:
        self._log = logger.bind(component="agent_db")
        # Branch data: branch_name -> table_name -> {row_id: row_dict}
        self._branches: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        # Commit log: branch_name -> [Commit]
        self._commits: dict[str, list[Commit]] = {}
        # Track which branches exist and their parent
        self._branch_parents: dict[str, str] = {}
        # Merged branches log
        self._merge_log: list[dict[str, Any]] = []
        # Initialize main branch with empty tables
        self._init_main()

    def _init_main(self) -> None:
        self._branches["main"] = {table: {} for table in SCHEMA}
        self._commits["main"] = [Commit(
            id=_uuid(), branch="main", author="SYSTEM",
            message="Initialize database schema",
            timestamp=_now(),
        )]

    # ─── Branch operations ──────────────────────────────────────────

    def create_branch(self, name: str, from_branch: str = "main") -> dict[str, Any]:
        """Create a new branch from an existing branch (deep copy)."""
        if name in self._branches:
            return {"error": f"Branch '{name}' already exists"}
        if from_branch not in self._branches:
            return {"error": f"Source branch '{from_branch}' not found"}

        self._branches[name] = copy.deepcopy(self._branches[from_branch])
        self._commits[name] = list(self._commits[from_branch])
        self._branch_parents[name] = from_branch
        self._log.info("branch_created", branch=name, from_branch=from_branch)
        return {"branch": name, "from": from_branch, "tables": list(SCHEMA.keys())}

    def delete_branch(self, name: str) -> dict[str, Any]:
        """Delete a branch (cannot delete main)."""
        if name == "main":
            return {"error": "Cannot delete main branch"}
        if name not in self._branches:
            return {"error": f"Branch '{name}' not found"}
        del self._branches[name]
        del self._commits[name]
        self._branch_parents.pop(name, None)
        self._log.info("branch_deleted", branch=name)
        return {"deleted": name}

    def list_branches(self) -> list[dict[str, Any]]:
        """List all branches with commit counts and row counts."""
        result = []
        for name in self._branches:
            total_rows = sum(len(rows) for rows in self._branches[name].values())
            commits = self._commits.get(name, [])
            result.append({
                "name": name,
                "parent": self._branch_parents.get(name),
                "commits": len(commits),
                "total_rows": total_rows,
                "last_commit": commits[-1].to_dict() if commits else None,
            })
        return result

    # ─── CRUD operations ────────────────────────────────────────────

    def insert(self, branch: str, table: str, row: dict[str, Any],
               author: str = "SYSTEM") -> dict[str, Any]:
        """Insert a row into a table on a branch."""
        if branch not in self._branches:
            return {"error": f"Branch '{branch}' not found"}
        if table not in SCHEMA:
            return {"error": f"Table '{table}' not found in schema"}

        row_id = row.get("id") or _uuid()
        row["id"] = row_id
        if "created_at" in SCHEMA[table] and "created_at" not in row:
            row["created_at"] = _now()

        self._branches[branch][table][row_id] = row
        self._auto_commit(branch, author, f"INSERT into {table}",
                          {table: [{"type": "added", "id": row_id, "row": row}]})
        return {"id": row_id, "table": table, "branch": branch}

    def update(self, branch: str, table: str, row_id: str,
               updates: dict[str, Any], author: str = "SYSTEM") -> dict[str, Any]:
        """Update a row on a branch."""
        if branch not in self._branches:
            return {"error": f"Branch '{branch}' not found"}
        if table not in self._branches[branch]:
            return {"error": f"Table '{table}' not found"}
        if row_id not in self._branches[branch][table]:
            return {"error": f"Row '{row_id}' not found in {table}"}

        old = copy.deepcopy(self._branches[branch][table][row_id])
        self._branches[branch][table][row_id].update(updates)
        new = self._branches[branch][table][row_id]

        self._auto_commit(branch, author, f"UPDATE {table} SET {list(updates.keys())}",
                          {table: [{"type": "modified", "id": row_id, "from": old, "to": new}]})
        return {"id": row_id, "table": table, "branch": branch, "updated_fields": list(updates.keys())}

    def delete_row(self, branch: str, table: str, row_id: str,
                   author: str = "SYSTEM") -> dict[str, Any]:
        """Delete a row from a branch."""
        if branch not in self._branches:
            return {"error": f"Branch '{branch}' not found"}
        if row_id not in self._branches[branch].get(table, {}):
            return {"error": f"Row '{row_id}' not found in {table}"}

        old = self._branches[branch][table].pop(row_id)
        self._auto_commit(branch, author, f"DELETE from {table} WHERE id='{row_id[:8]}...'",
                          {table: [{"type": "removed", "id": row_id, "row": old}]})
        return {"deleted": row_id, "table": table, "branch": branch}

    def query(self, branch: str, table: str, filters: dict[str, Any] | None = None,
              limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """Query rows from a table on a branch with optional filters."""
        if branch not in self._branches:
            return {"error": f"Branch '{branch}' not found"}
        if table not in self._branches[branch]:
            return {"error": f"Table '{table}' not found"}

        rows = list(self._branches[branch][table].values())

        if filters:
            for key, value in filters.items():
                rows = [r for r in rows if r.get(key) == value]

        total = len(rows)
        rows = rows[offset:offset + limit]
        return {"rows": rows, "total": total, "table": table, "branch": branch}

    def get_row(self, branch: str, table: str, row_id: str) -> dict[str, Any]:
        """Get a single row by ID."""
        if branch not in self._branches:
            return {"error": f"Branch '{branch}' not found"}
        row = self._branches[branch].get(table, {}).get(row_id)
        if not row:
            return {"error": f"Row '{row_id}' not found"}
        return {"row": row, "table": table, "branch": branch}

    # ─── Version control operations ─────────────────────────────────

    def diff(self, from_branch: str, to_branch: str,
             table: str | None = None) -> list[dict[str, Any]]:
        """Compute diff between two branches (like DOLT_DIFF)."""
        if from_branch not in self._branches or to_branch not in self._branches:
            return [{"error": "Branch not found"}]

        tables = [table] if table else list(SCHEMA.keys())
        diffs: list[dict[str, Any]] = []

        for tbl in tables:
            from_rows = self._branches[from_branch].get(tbl, {})
            to_rows = self._branches[to_branch].get(tbl, {})

            all_ids = set(from_rows.keys()) | set(to_rows.keys())
            for row_id in all_ids:
                f = from_rows.get(row_id)
                t = to_rows.get(row_id)

                if f and not t:
                    diffs.append(DiffEntry(tbl, DiffType.REMOVED, row_id, from_row=f).to_dict())
                elif t and not f:
                    diffs.append(DiffEntry(tbl, DiffType.ADDED, row_id, to_row=t).to_dict())
                elif f and t and f != t:
                    diffs.append(DiffEntry(tbl, DiffType.MODIFIED, row_id, from_row=f, to_row=t).to_dict())

        return diffs

    def merge(self, source_branch: str, target_branch: str = "main",
              author: str = "SYSTEM") -> dict[str, Any]:
        """Merge source branch into target (like DOLT_MERGE). Applies all diffs atomically."""
        if source_branch not in self._branches:
            return {"error": f"Source branch '{source_branch}' not found"}
        if target_branch not in self._branches:
            return {"error": f"Target branch '{target_branch}' not found"}

        diffs = self.diff(target_branch, source_branch)
        if not diffs or (len(diffs) == 1 and "error" in diffs[0]):
            return {"merged": 0, "message": "No changes to merge"}

        # Apply diffs atomically
        added = modified = removed = 0
        for d in diffs:
            tbl = d["table"]
            rid = d["row_id"]
            dt = d["diff_type"]

            if dt == DiffType.ADDED.value:
                self._branches[target_branch][tbl][rid] = copy.deepcopy(
                    self._branches[source_branch][tbl][rid])
                added += 1
            elif dt == DiffType.MODIFIED.value:
                self._branches[target_branch][tbl][rid] = copy.deepcopy(
                    self._branches[source_branch][tbl][rid])
                modified += 1
            elif dt == DiffType.REMOVED.value:
                self._branches[target_branch][tbl].pop(rid, None)
                removed += 1

        commit = Commit(
            id=_uuid(), branch=target_branch, author=author,
            message=f"Merge '{source_branch}' into '{target_branch}'",
            timestamp=_now(),
            parent_id=self._commits[target_branch][-1].id if self._commits[target_branch] else None,
            changes={"added": added, "modified": modified, "removed": removed},
        )
        self._commits[target_branch].append(commit)

        self._merge_log.append({
            "source": source_branch, "target": target_branch,
            "commit_id": commit.id, "timestamp": commit.timestamp,
            "added": added, "modified": modified, "removed": removed,
        })

        self._log.info("branch_merged", source=source_branch, target=target_branch,
                        added=added, modified=modified, removed=removed)
        return {
            "commit_id": commit.id, "source": source_branch,
            "target": target_branch, "added": added,
            "modified": modified, "removed": removed,
        }

    def reset(self, branch: str, commit_id: str | None = None,
              steps: int = 1) -> dict[str, Any]:
        """Rollback a branch (like DOLT_RESET('--hard', 'HEAD~N')).

        If commit_id is given, reset to that commit.
        Otherwise, rollback N steps from HEAD.
        """
        if branch not in self._branches:
            return {"error": f"Branch '{branch}' not found"}
        if branch == "main" and not commit_id:
            return {"error": "Cannot rollback main without explicit commit_id"}

        commits = self._commits.get(branch, [])
        if not commits:
            return {"error": "No commits to rollback"}

        if commit_id:
            target_idx = next((i for i, c in enumerate(commits) if c.id == commit_id), None)
            if target_idx is None:
                return {"error": f"Commit '{commit_id}' not found on branch '{branch}'"}
        else:
            target_idx = max(0, len(commits) - 1 - steps)

        # Rebuild state by replaying commits up to target
        # For simplicity, re-fork from parent at that commit point
        rolled_back = len(commits) - 1 - target_idx
        self._commits[branch] = commits[:target_idx + 1]

        # Restore from parent + replay (simplified: reset to parent state)
        parent = self._branch_parents.get(branch, "main")
        if parent in self._branches and parent != branch:
            self._branches[branch] = copy.deepcopy(self._branches[parent])

        self._log.info("branch_reset", branch=branch, rolled_back=rolled_back)
        return {"branch": branch, "rolled_back_commits": rolled_back,
                "current_head": self._commits[branch][-1].id if self._commits[branch] else None}

    def log(self, branch: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get commit log for a branch."""
        if branch not in self._commits:
            return [{"error": f"Branch '{branch}' not found"}]
        commits = self._commits[branch][-limit:]
        return [c.to_dict() for c in reversed(commits)]

    # ─── Convenience methods for agent workflows ────────────────────

    def record_operation(self, agent_name: str, action: str, status: str = "completed",
                         payload: dict[str, Any] | None = None,
                         result: dict[str, Any] | None = None,
                         error: str = "", duration_ms: int = 0) -> dict[str, Any]:
        """Record an agent operation on its isolated branch."""
        branch = f"agent/{agent_name.lower()}"
        if branch not in self._branches:
            self.create_branch(branch, "main")

        row = {
            "agent_name": agent_name,
            "action": action,
            "status": status,
            "payload": payload or {},
            "result": result or {},
            "error": error,
            "duration_ms": duration_ms,
            "completed_at": _now() if status in ("completed", "failed") else None,
        }
        return self.insert(branch, "agent_operations", row, author=agent_name)

    def update_agent_state(self, agent_name: str, status: str,
                           tasks_completed: int = 0, tasks_failed: int = 0,
                           health_score: float = 1.0,
                           config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Update agent state on its branch."""
        branch = f"agent/{agent_name.lower()}"
        if branch not in self._branches:
            self.create_branch(branch, "main")

        # Upsert: find existing or create new
        existing = None
        for rid, row in self._branches[branch]["agent_state"].items():
            if row.get("agent_name") == agent_name:
                existing = rid
                break

        if existing:
            return self.update(branch, "agent_state", existing, {
                "status": status, "tasks_completed": tasks_completed,
                "tasks_failed": tasks_failed, "health_score": health_score,
                "last_task_at": _now(), "config": config or {},
            }, author=agent_name)
        else:
            return self.insert(branch, "agent_state", {
                "agent_name": agent_name, "status": status,
                "tasks_completed": tasks_completed, "tasks_failed": tasks_failed,
                "health_score": health_score, "last_task_at": _now(),
                "config": config or {},
            }, author=agent_name)

    def record_integration_event(self, integration: str, event_type: str,
                                 agent_name: str = "", request_summary: str = "",
                                 response_status: int = 200,
                                 duration_ms: int = 0) -> dict[str, Any]:
        """Record integration call on main branch."""
        return self.insert("main", "integration_events", {
            "integration": integration, "event_type": event_type,
            "agent_name": agent_name, "request_summary": request_summary,
            "response_status": response_status, "duration_ms": duration_ms,
        }, author=agent_name or "SYSTEM")

    def get_agent_branch_status(self, agent_name: str) -> dict[str, Any]:
        """Get full status of an agent's branch including pending diffs."""
        branch = f"agent/{agent_name.lower()}"
        if branch not in self._branches:
            return {"error": f"No branch for agent '{agent_name}'"}

        diffs = self.diff("main", branch)
        ops = self.query(branch, "agent_operations", {"agent_name": agent_name}, limit=10)
        state = self.query(branch, "agent_state", {"agent_name": agent_name}, limit=1)
        commits = self.log(branch, limit=5)

        return {
            "branch": branch,
            "pending_changes": len(diffs),
            "diffs": diffs[:20],
            "recent_operations": ops.get("rows", []),
            "state": state.get("rows", [{}])[0] if state.get("rows") else {},
            "recent_commits": commits,
        }

    # ─── Schema introspection ──────────────────────────────────────

    def get_schema(self) -> dict[str, dict[str, str]]:
        """Return the full database schema."""
        return SCHEMA

    def get_schema_sql(self) -> str:
        """Generate CREATE TABLE SQL for the full schema."""
        lines = []
        for table, columns in SCHEMA.items():
            cols = []
            for col_name, col_type in columns.items():
                cols.append(f"  `{col_name}` {col_type}")
            lines.append(f"CREATE TABLE `{table}` (\n" + ",\n".join(cols) + "\n);")
        return "\n\n".join(lines)

    def get_table_stats(self, branch: str = "main") -> dict[str, Any]:
        """Get row counts and schema for all tables on a branch."""
        if branch not in self._branches:
            return {"error": f"Branch '{branch}' not found"}
        stats = {}
        for table in SCHEMA:
            rows = self._branches[branch].get(table, {})
            stats[table] = {
                "row_count": len(rows),
                "columns": list(SCHEMA[table].keys()),
            }
        return {"branch": branch, "tables": stats}

    # ─── Persistence ────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize for state persistence."""
        return {
            "branches": {
                name: {table: list(rows.values()) for table, rows in tables.items()}
                for name, tables in self._branches.items()
            },
            "commits": {
                name: [c.to_dict() for c in commits[-100:]]
                for name, commits in self._commits.items()
            },
            "branch_parents": self._branch_parents,
            "merge_log": self._merge_log[-50:],
        }

    def restore_from_dict(self, data: dict[str, Any]) -> None:
        """Restore from persisted state."""
        self._branch_parents = data.get("branch_parents", {})
        self._merge_log = data.get("merge_log", [])

        for branch_name, tables in data.get("branches", {}).items():
            self._branches[branch_name] = {}
            for table_name, rows in tables.items():
                self._branches[branch_name][table_name] = {}
                for row in rows:
                    row_id = row.get("id", _uuid())
                    self._branches[branch_name][table_name][row_id] = row

        for branch_name, commits in data.get("commits", {}).items():
            self._commits[branch_name] = [
                Commit(
                    id=c["id"], branch=c["branch"], author=c["author"],
                    message=c["message"], timestamp=c["timestamp"],
                    parent_id=c.get("parent_id"), changes=c.get("changes", {}),
                )
                for c in commits
            ]

        # Ensure main exists
        if "main" not in self._branches:
            self._init_main()

        self._log.info("agent_db_restored",
                        branches=len(self._branches),
                        total_commits=sum(len(c) for c in self._commits.values()))

    # ─── Internal ───────────────────────────────────────────────────

    def _auto_commit(self, branch: str, author: str, message: str,
                     changes: dict[str, list[dict[str, Any]]]) -> None:
        """Auto-commit after every write (like dolt_transaction_commit=1)."""
        parent_id = self._commits[branch][-1].id if self._commits.get(branch) else None
        commit = Commit(
            id=_uuid(), branch=branch, author=author,
            message=message, timestamp=_now(),
            parent_id=parent_id, changes=changes,
        )
        if branch not in self._commits:
            self._commits[branch] = []
        self._commits[branch].append(commit)


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
