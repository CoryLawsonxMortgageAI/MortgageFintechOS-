"""Reference Store — manages knowledge base markdown files for agent prompts and skills.

Loads and indexes markdown files (Claude.md, Kimi2.5.md, etc.) from the
knowledge/refs/ directory. Agents can query the store for prompt templates,
skill definitions, and domain knowledge to enhance their capabilities.

Features:
- Auto-loads all .md files from knowledge/refs/ on startup
- Section-based retrieval (query by heading)
- Keyword search across all reference files
- Hot-reload: detects file changes without restart
- API endpoint for managing references via dashboard
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

REFS_DIR = Path(__file__).parent / "refs"


class ReferenceFile:
    """A parsed markdown reference file."""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.raw_content: str = ""
        self.sections: dict[str, str] = {}
        self.metadata: dict[str, str] = {}
        self.loaded_at: datetime | None = None
        self._mtime: float = 0

    def load(self) -> None:
        """Load and parse the markdown file."""
        if not self.path.exists():
            return
        self._mtime = self.path.stat().st_mtime
        self.raw_content = self.path.read_text(encoding="utf-8")
        self.loaded_at = datetime.now(timezone.utc)
        self._parse_sections()
        self._parse_metadata()

    def is_stale(self) -> bool:
        """Check if the file has been modified since last load."""
        if not self.path.exists():
            return False
        return self.path.stat().st_mtime > self._mtime

    def _parse_sections(self) -> None:
        """Parse markdown into sections by heading."""
        self.sections = {}
        current_heading = "_intro"
        current_lines: list[str] = []

        for line in self.raw_content.split("\n"):
            heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
            if heading_match:
                # Save previous section
                if current_lines:
                    self.sections[current_heading] = "\n".join(current_lines).strip()
                current_heading = heading_match.group(2).strip()
                current_lines = []
            else:
                current_lines.append(line)

        # Save last section
        if current_lines:
            self.sections[current_heading] = "\n".join(current_lines).strip()

    def _parse_metadata(self) -> None:
        """Extract YAML-style metadata from frontmatter if present."""
        self.metadata = {}
        if self.raw_content.startswith("---"):
            parts = self.raw_content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        key, _, value = line.partition(":")
                        self.metadata[key.strip()] = value.strip()

    def get_section(self, heading: str) -> str:
        """Get content of a specific section by heading."""
        return self.sections.get(heading, "")

    def search(self, keyword: str) -> list[dict[str, str]]:
        """Search for a keyword across all sections."""
        results = []
        keyword_lower = keyword.lower()
        for heading, content in self.sections.items():
            if keyword_lower in content.lower() or keyword_lower in heading.lower():
                results.append({
                    "file": self.name,
                    "section": heading,
                    "snippet": self._extract_snippet(content, keyword_lower),
                })
        return results

    def _extract_snippet(self, content: str, keyword: str, context: int = 100) -> str:
        """Extract a snippet around the keyword match."""
        idx = content.lower().find(keyword)
        if idx == -1:
            return content[:200]
        start = max(0, idx - context)
        end = min(len(content), idx + len(keyword) + context)
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path),
            "sections": list(self.sections.keys()),
            "metadata": self.metadata,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "size_bytes": len(self.raw_content),
        }


class ReferenceStore:
    """Manages all reference markdown files for agent use."""

    def __init__(self, refs_dir: str | Path | None = None):
        self._refs_dir = Path(refs_dir) if refs_dir else REFS_DIR
        self._files: dict[str, ReferenceFile] = {}
        self._log = logger.bind(component="reference_store")

    def start(self) -> None:
        """Load all reference files from the refs directory."""
        self._refs_dir.mkdir(parents=True, exist_ok=True)
        self._load_all()
        self._log.info("reference_store_started", files=len(self._files), dir=str(self._refs_dir))

    def _load_all(self) -> None:
        """Scan and load all .md files."""
        for path in sorted(self._refs_dir.glob("*.md")):
            name = path.stem
            ref = ReferenceFile(name=name, path=path)
            ref.load()
            self._files[name] = ref
            self._log.info("reference_loaded", file=name, sections=len(ref.sections))

    def reload_if_stale(self) -> list[str]:
        """Check for modified files and reload them. Returns list of reloaded file names."""
        reloaded = []
        # Check existing files
        for name, ref in self._files.items():
            if ref.is_stale():
                ref.load()
                reloaded.append(name)
        # Check for new files
        for path in self._refs_dir.glob("*.md"):
            name = path.stem
            if name not in self._files:
                ref = ReferenceFile(name=name, path=path)
                ref.load()
                self._files[name] = ref
                reloaded.append(name)
        if reloaded:
            self._log.info("references_reloaded", files=reloaded)
        return reloaded

    def get(self, name: str) -> ReferenceFile | None:
        """Get a reference file by name (without .md extension)."""
        return self._files.get(name)

    def get_section(self, file_name: str, section: str) -> str:
        """Get a specific section from a reference file."""
        ref = self._files.get(file_name)
        if ref:
            return ref.get_section(section)
        return ""

    def get_prompt_context(self, file_name: str, sections: list[str] | None = None) -> str:
        """Get formatted content from a reference file for use as prompt context.

        If sections is None, returns the full file content.
        If sections is specified, returns only those sections joined together.
        """
        ref = self._files.get(file_name)
        if not ref:
            return ""
        if sections is None:
            return ref.raw_content
        parts = []
        for s in sections:
            content = ref.get_section(s)
            if content:
                parts.append(f"## {s}\n{content}")
        return "\n\n".join(parts)

    def search(self, keyword: str) -> list[dict[str, str]]:
        """Search across all reference files for a keyword."""
        results = []
        for ref in self._files.values():
            results.extend(ref.search(keyword))
        return results

    def list_files(self) -> list[dict[str, Any]]:
        """List all loaded reference files."""
        return [ref.to_dict() for ref in self._files.values()]

    def save_file(self, name: str, content: str) -> dict[str, Any]:
        """Save or update a reference file."""
        path = self._refs_dir / f"{name}.md"
        path.write_text(content, encoding="utf-8")

        ref = ReferenceFile(name=name, path=path)
        ref.load()
        self._files[name] = ref
        self._log.info("reference_saved", file=name, sections=len(ref.sections))
        return ref.to_dict()

    def delete_file(self, name: str) -> bool:
        """Delete a reference file."""
        ref = self._files.pop(name, None)
        if ref and ref.path.exists():
            ref.path.unlink()
            self._log.info("reference_deleted", file=name)
            return True
        return False

    def get_status(self) -> dict[str, Any]:
        return {
            "refs_dir": str(self._refs_dir),
            "total_files": len(self._files),
            "files": list(self._files.keys()),
        }
