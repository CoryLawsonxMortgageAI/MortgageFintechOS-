"""JSON-file state persistence for MortgageFintechOS.

Provides atomic writes with debouncing to avoid I/O thrash while
ensuring agent state survives process restarts.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class StateStore:
    """Persists state to JSON files with atomic writes and debounced flushing."""

    def __init__(self, data_dir: str = "data"):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._pending: dict[str, dict[str, Any]] = {}
        self._flush_task: asyncio.Task[None] | None = None
        self._running = False
        self._flush_interval = 5  # seconds
        self._log = logger.bind(component="state_store")

    async def start(self) -> None:
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        self._log.info("state_store_started", data_dir=str(self._data_dir))

    async def stop(self) -> None:
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        self._log.info("state_store_stopped")

    async def save(self, key: str, data: dict[str, Any]) -> None:
        """Write data to disk immediately with atomic rename."""
        path = self._data_dir / f"{key}.json"
        tmp_path = self._data_dir / f"{key}.json.tmp"
        payload = json.dumps(data, default=_json_default, indent=2)
        try:
            tmp_path.write_text(payload)
            os.replace(str(tmp_path), str(path))
        except Exception as e:
            self._log.error("state_save_failed", key=key, error=str(e))

    async def load(self, key: str) -> dict[str, Any] | None:
        """Read data from disk. Returns None if file does not exist."""
        path = self._data_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            text = path.read_text()
            return json.loads(text)
        except (json.JSONDecodeError, OSError) as e:
            self._log.error("state_load_failed", key=key, error=str(e))
            return None

    async def save_debounced(self, key: str, data: dict[str, Any]) -> None:
        """Buffer a write — it will be flushed within flush_interval seconds."""
        self._pending[key] = data

    async def flush(self) -> None:
        """Force write all pending data to disk."""
        pending = dict(self._pending)
        self._pending.clear()
        for key, data in pending.items():
            await self.save(key, data)
        if pending:
            self._log.info("state_flushed", keys=list(pending.keys()))

    async def _flush_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._flush_interval)
            if self._pending:
                await self.flush()


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
