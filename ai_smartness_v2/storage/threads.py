"""
ThreadStorage - CRUD operations for Thread entities.
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models.thread import Thread, ThreadStatus


class ThreadStorage:
    """
    Storage layer for Thread entities.

    Handles CRUD operations and indexing by status.
    """

    def __init__(self, threads_path: Path):
        """
        Initialize thread storage.

        Args:
            threads_path: Path to threads directory
        """
        self.path = Path(threads_path)
        self.path.mkdir(parents=True, exist_ok=True)

        # Index files
        self._active_index_path = self.path / "_active.json"
        self._suspended_index_path = self.path / "_suspended.json"

        # Ensure indexes exist
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Ensure index files exist."""
        for index_path in [self._active_index_path, self._suspended_index_path]:
            if not index_path.exists():
                self._write_json(index_path, {"threads": [], "last_updated": datetime.now().isoformat()})

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

    def _thread_path(self, thread_id: str) -> Path:
        """Get path for a thread file."""
        return self.path / f"{thread_id}.json"

    def save(self, thread: Thread) -> Thread:
        """
        Save a thread to storage.

        Args:
            thread: Thread to save

        Returns:
            The saved thread
        """
        # Write thread file
        self._write_json(self._thread_path(thread.id), thread.to_dict())

        # Update indexes
        self._update_indexes(thread)

        return thread

    def get(self, thread_id: str) -> Optional[Thread]:
        """
        Get a thread by ID.

        Args:
            thread_id: Thread ID

        Returns:
            Thread if found, None otherwise
        """
        data = self._read_json(self._thread_path(thread_id))
        if data is None:
            return None
        return Thread.from_dict(data)

    def delete(self, thread_id: str) -> bool:
        """
        Delete a thread.

        Args:
            thread_id: Thread ID to delete

        Returns:
            True if deleted, False if not found
        """
        path = self._thread_path(thread_id)
        if not path.exists():
            return False

        path.unlink()
        self._remove_from_indexes(thread_id)
        return True

    def get_active(self) -> List[Thread]:
        """Get all active threads."""
        index = self._read_json(self._active_index_path) or {"threads": []}
        threads = []
        for tid in index.get("threads", []):
            thread = self.get(tid)
            if thread and thread.status == ThreadStatus.ACTIVE:
                threads.append(thread)
        return threads

    def get_suspended(self) -> List[Thread]:
        """Get all suspended threads."""
        index = self._read_json(self._suspended_index_path) or {"threads": []}
        threads = []
        for tid in index.get("threads", []):
            thread = self.get(tid)
            if thread and thread.status == ThreadStatus.SUSPENDED:
                threads.append(thread)
        return threads

    def get_archived(self) -> List[Thread]:
        """Get all archived threads."""
        archived = []
        for thread_file in self.path.glob("thread_*.json"):
            thread = self.get(thread_file.stem)
            if thread and thread.status == ThreadStatus.ARCHIVED:
                archived.append(thread)
        return archived

    def get_all(self) -> List[Thread]:
        """Get all threads."""
        threads = []
        for thread_file in self.path.glob("thread_*.json"):
            thread = self.get(thread_file.stem)
            if thread:
                threads.append(thread)
        return threads

    def get_current(self) -> Optional[Thread]:
        """
        Get the current (most recently active) thread.

        Returns:
            Most recent active thread, or None if no active threads
        """
        active = self.get_active()
        if not active:
            return None

        # Sort by last_active, return most recent
        active.sort(key=lambda t: t.last_active, reverse=True)
        return active[0]

    def find_by_topics(self, topics: List[str], limit: int = 10) -> List[Thread]:
        """
        Find threads by topics.

        Args:
            topics: List of topics to search for
            limit: Maximum number of results

        Returns:
            List of threads matching any of the topics
        """
        topics_lower = set(t.lower() for t in topics)
        matches = []

        for thread in self.get_all():
            thread_topics = set(t.lower() for t in thread.topics)
            if thread_topics & topics_lower:
                overlap = len(thread_topics & topics_lower)
                matches.append((overlap, thread))

        # Sort by overlap count (descending)
        matches.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in matches[:limit]]

    def _update_indexes(self, thread: Thread):
        """Update index files after thread change."""
        # Update active index
        active_index = self._read_json(self._active_index_path) or {"threads": []}
        active_list = active_index.get("threads", [])

        # Update suspended index
        suspended_index = self._read_json(self._suspended_index_path) or {"threads": []}
        suspended_list = suspended_index.get("threads", [])

        # Remove from both first
        if thread.id in active_list:
            active_list.remove(thread.id)
        if thread.id in suspended_list:
            suspended_list.remove(thread.id)

        # Add to appropriate index
        if thread.status == ThreadStatus.ACTIVE:
            if thread.id not in active_list:
                active_list.append(thread.id)
        elif thread.status == ThreadStatus.SUSPENDED:
            if thread.id not in suspended_list:
                suspended_list.append(thread.id)

        # Write indexes
        active_index["threads"] = active_list
        active_index["last_updated"] = datetime.now().isoformat()
        self._write_json(self._active_index_path, active_index)

        suspended_index["threads"] = suspended_list
        suspended_index["last_updated"] = datetime.now().isoformat()
        self._write_json(self._suspended_index_path, suspended_index)

    def _remove_from_indexes(self, thread_id: str):
        """Remove a thread from all indexes."""
        for index_path in [self._active_index_path, self._suspended_index_path]:
            index = self._read_json(index_path) or {"threads": []}
            if thread_id in index.get("threads", []):
                index["threads"].remove(thread_id)
                index["last_updated"] = datetime.now().isoformat()
                self._write_json(index_path, index)
