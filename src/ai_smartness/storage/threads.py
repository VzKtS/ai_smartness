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

    def prune_threads(self, mode_quota: int = None) -> int:
        """
        Apply decay and suspend threads below threshold or over quota.

        Unlike bridges, threads are suspended not deleted.

        Args:
            mode_quota: Optional quota to enforce (suspends excess threads)

        Returns:
            Number of threads suspended
        """
        from ..models.thread import Thread as ThreadModel

        active_threads = self.get_active()
        suspended_count = 0

        # Apply decay to all active threads
        for thread in active_threads:
            should_suspend = thread.decay()

            if should_suspend:
                thread.suspend("auto_decay")
                self.save(thread)
                suspended_count += 1
            else:
                # Save updated weight
                self.save(thread)

        # Enforce quota if specified
        if mode_quota is not None:
            # Re-get active (some may have been suspended)
            active_threads = self.get_active()

            if len(active_threads) > mode_quota:
                # Sort by weight (lowest first)
                active_threads.sort(key=lambda t: t.weight)

                # Suspend excess
                excess = len(active_threads) - mode_quota
                for thread in active_threads[:excess]:
                    thread.suspend("quota_exceeded")
                    self.save(thread)
                    suspended_count += 1

        return suspended_count

    def get_weight_stats(self) -> dict:
        """
        Get weight statistics for all threads.

        Returns:
            Dict with min, max, avg, active_count, suspended_count
        """
        all_threads = self.get_all()

        if not all_threads:
            return {
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "active_count": 0,
                "suspended_count": 0,
                "total": 0
            }

        weights = [t.weight for t in all_threads]
        active = [t for t in all_threads if t.status == ThreadStatus.ACTIVE]
        suspended = [t for t in all_threads if t.status == ThreadStatus.SUSPENDED]

        return {
            "min": min(weights),
            "max": max(weights),
            "avg": sum(weights) / len(weights),
            "active_count": len(active),
            "suspended_count": len(suspended),
            "total": len(all_threads)
        }

    def enforce_quota(self, quota: int) -> int:
        """
        Enforce a specific quota on active threads.

        Suspends lowest-weight threads when over quota.

        Args:
            quota: Maximum number of active threads

        Returns:
            Number of threads suspended
        """
        active_threads = self.get_active()

        if len(active_threads) <= quota:
            return 0

        # Sort by weight (lowest first)
        active_threads.sort(key=lambda t: t.weight)

        # Suspend excess
        suspended_count = 0
        excess = len(active_threads) - quota
        for thread in active_threads[:excess]:
            thread.suspend("quota_change")
            self.save(thread)
            suspended_count += 1

        return suspended_count

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

    # =========================================================================
    # MERGE & SPLIT (v4.3)
    # =========================================================================

    def merge(self, survivor_id: str, absorbed_id: str) -> Optional[Thread]:
        """
        Merge two threads into one.

        The survivor thread absorbs the absorbed thread:
        - Messages from absorbed are added to survivor (sorted by timestamp)
        - Topics/tags are merged (union)
        - Weight = max(both) + 0.1 boost
        - Absorbed thread is archived with tag 'merged_into:<survivor_id>'

        Args:
            survivor_id: Thread that will remain active
            absorbed_id: Thread to be absorbed and archived

        Returns:
            The merged survivor thread, or None if failed
        """
        survivor = self.get(survivor_id)
        absorbed = self.get(absorbed_id)

        if not survivor or not absorbed:
            return None

        # Check split_locked - can't merge locked threads
        if absorbed.split_locked:
            return None

        # 1. Merge messages (sorted by timestamp)
        all_messages = survivor.messages + absorbed.messages
        all_messages.sort(key=lambda m: m.timestamp)
        survivor.messages = all_messages

        # 2. Merge topics and tags (union, deduplicated)
        survivor.topics = list(set(survivor.topics + absorbed.topics))
        survivor.tags = list(set(survivor.tags + absorbed.tags))

        # 3. Merge summary
        if absorbed.summary and survivor.summary:
            survivor.summary = f"{survivor.summary}\n---\n{absorbed.summary}"
        elif absorbed.summary:
            survivor.summary = absorbed.summary

        # 4. Boost weight
        survivor.weight = min(1.0, max(survivor.weight, absorbed.weight) + 0.1)
        survivor.last_active = datetime.now()
        survivor.activation_count += 1

        # 5. Clear embedding (needs recalculation)
        survivor.embedding = None

        # 6. Archive absorbed thread with merge tag
        absorbed.archive()
        absorbed.tags.append(f"merged_into:{survivor_id}")

        # 7. Save both
        self.save(survivor)
        self.save(absorbed)

        return survivor

    def split(
        self,
        thread_id: str,
        split_config: List[dict],
        lock_until: str = "compaction"
    ) -> List[Thread]:
        """
        Split a thread into multiple new threads.

        Args:
            thread_id: Thread to split
            split_config: List of dicts with 'title' and 'message_ids'
                Example: [{"title": "Topic A", "message_ids": ["msg_1", "msg_2"]}]
            lock_until: Lock mode for new threads ("compaction"|"agent_release"|"force")

        Returns:
            List of newly created threads (empty if failed)
        """
        parent = self.get(thread_id)
        if not parent:
            return []

        # Validate lock_until
        valid_locks = {"compaction", "agent_release", "force"}
        if lock_until not in valid_locks:
            lock_until = "compaction"

        new_threads = []
        used_message_ids = set()

        for config in split_config:
            title = config.get("title", "Split thread")
            message_ids = set(config.get("message_ids", []))
            topics = config.get("topics", [])

            if not message_ids:
                continue

            # Extract messages for this new thread
            extracted_messages = []
            for msg in parent.messages:
                if msg.id in message_ids:
                    extracted_messages.append(msg)
                    used_message_ids.add(msg.id)

            if not extracted_messages:
                continue

            # Create new thread
            from ..models.thread import Thread as ThreadModel, OriginType
            new_thread = ThreadModel.create(
                title=title,
                origin_type=OriginType.SPLIT,
                parent_id=thread_id
            )
            new_thread.messages = extracted_messages
            new_thread.topics = topics or parent.topics.copy()
            new_thread.weight = parent.weight * 0.8  # Inherit reduced weight
            new_thread.split_locked = True  # Always locked
            new_thread.split_locked_until = lock_until

            # Save new thread
            self.save(new_thread)
            new_threads.append(new_thread)

            # Update parent's child_ids
            parent.add_child(new_thread.id)

        # Remove extracted messages from parent
        parent.messages = [m for m in parent.messages if m.id not in used_message_ids]

        # Clear parent embedding (needs recalculation)
        parent.embedding = None

        # Save parent
        self.save(parent)

        return new_threads

    def unlock(self, thread_id: str) -> bool:
        """
        Remove split_lock from a thread.

        Args:
            thread_id: Thread to unlock

        Returns:
            True if unlocked, False if not found or not locked
        """
        thread = self.get(thread_id)
        if not thread:
            return False

        if not thread.split_locked:
            return False

        thread.split_locked = False
        thread.split_locked_until = None
        self.save(thread)
        return True

    def unlock_compacted(self) -> int:
        """
        Unlock all threads with split_locked_until='compaction'.

        Called after a compaction event.

        Returns:
            Number of threads unlocked
        """
        unlocked = 0

        for thread in self.get_all():
            if thread.split_locked and thread.split_locked_until == "compaction":
                thread.split_locked = False
                thread.split_locked_until = None
                self.save(thread)
                unlocked += 1

        return unlocked

    def get_split_info(self, thread_id: str) -> Optional[dict]:
        """
        Get thread info for split workflow (step 1).

        Returns thread title and list of messages with IDs.

        Args:
            thread_id: Thread ID

        Returns:
            Dict with thread info, or None if not found
        """
        thread = self.get(thread_id)
        if not thread:
            return None

        messages_info = []
        for msg in thread.messages:
            preview = msg.content[:80].replace('\n', ' ')
            messages_info.append({
                "id": msg.id,
                "source": msg.source,
                "preview": f"{preview}..."
            })

        return {
            "id": thread.id,
            "title": thread.title,
            "message_count": len(thread.messages),
            "messages": messages_info
        }
