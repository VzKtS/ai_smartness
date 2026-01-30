"""
StorageManager - Central storage coordinator for AI Smartness v2.

Manages the database structure and provides access to specialized storage classes.
"""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime


class StorageManager:
    """
    Central storage coordinator.

    Initializes and manages the database structure.
    Provides access to ThreadStorage and BridgeStorage.
    """

    DB_STRUCTURE = {
        "threads": {},
        "bridges": {},
    }

    def __init__(self, root_path: Path):
        """
        Initialize storage manager.

        Args:
            root_path: Root path of ai_smartness-v2 installation
        """
        self.root_path = Path(root_path)
        self.ai_path = self.root_path / ".ai"
        self.db_path = self.ai_path / "db"

        # Ensure structure exists
        self._ensure_structure()

        # Lazy-loaded storage instances
        self._thread_storage: Optional["ThreadStorage"] = None
        self._bridge_storage: Optional["BridgeStorage"] = None

    def _ensure_structure(self):
        """Ensure database directory structure exists."""
        for subdir in self.DB_STRUCTURE.keys():
            (self.db_path / subdir).mkdir(parents=True, exist_ok=True)

        # Create meta file if not exists
        meta_path = self.db_path / "_meta.json"
        if not meta_path.exists():
            meta = {
                "version": "2.2.0",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            self._write_json(meta_path, meta)

    @property
    def threads(self) -> "ThreadStorage":
        """Get ThreadStorage instance (lazy-loaded)."""
        if self._thread_storage is None:
            from .threads import ThreadStorage
            self._thread_storage = ThreadStorage(self.db_path / "threads")
        return self._thread_storage

    @property
    def bridges(self) -> "BridgeStorage":
        """Get BridgeStorage instance (lazy-loaded)."""
        if self._bridge_storage is None:
            from .bridges import BridgeStorage
            self._bridge_storage = BridgeStorage(self.db_path / "bridges")
        return self._bridge_storage

    def _write_json(self, path: Path, data: dict):
        """Write JSON file atomically."""
        temp_path = path.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            temp_path.rename(path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _read_json(self, path: Path) -> Optional[dict]:
        """Read JSON file safely."""
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return None

    def update_meta(self):
        """Update the meta file with current timestamp."""
        meta_path = self.db_path / "_meta.json"
        meta = self._read_json(meta_path) or {}
        meta["last_updated"] = datetime.now().isoformat()
        self._write_json(meta_path, meta)

    def get_stats(self) -> dict:
        """Get database statistics."""
        thread_count = len(list((self.db_path / "threads").glob("thread_*.json")))
        bridge_count = len(list((self.db_path / "bridges").glob("bridge_*.json")))

        return {
            "threads": thread_count,
            "bridges": bridge_count,
            "db_path": str(self.db_path)
        }

    def clear_all(self, confirm: bool = False):
        """
        Clear all data. Requires explicit confirmation.

        Args:
            confirm: Must be True to actually clear data
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to clear all data")

        # Clear threads
        for f in (self.db_path / "threads").glob("*.json"):
            f.unlink()

        # Clear bridges
        for f in (self.db_path / "bridges").glob("*.json"):
            f.unlink()

        # Reset meta
        self._ensure_structure()
