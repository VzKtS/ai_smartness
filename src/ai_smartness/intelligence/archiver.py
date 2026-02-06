"""
Archiver - Thread archival with LLM synthesis.

When threads are pruned (suspended too long), they are archived:
1. LLM generates a condensed synthesis of the thread content
2. Related bridges are indexed
3. Archive is stored in lightweight format
4. Original thread JSON files are deleted from disk
5. Orphan bridges are cleaned up
"""

import json
import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import uuid

from ..storage.manager import StorageManager
from ..models.thread import Thread, ThreadStatus

logger = logging.getLogger(__name__)

# Guard to prevent hook loops when calling LLM
HOOK_GUARD_ENV = "AI_SMARTNESS_HOOK_RUNNING"


class Archiver:
    """
    Archives threads with LLM-generated synthesis.

    Creates condensed archive records that preserve essential knowledge
    while freeing disk space by removing full thread JSON files.
    """

    # Threads suspended longer than this are candidates for archival
    ARCHIVE_AFTER_HOURS: int = 72  # 3 days

    def __init__(self, storage: StorageManager):
        self.storage = storage
        self.archives_path = storage.ai_path / "db" / "archives"
        self.archives_path.mkdir(parents=True, exist_ok=True)

    def archive_stale_threads(self) -> dict:
        """
        Find and archive threads that have been suspended > ARCHIVE_AFTER_HOURS.

        Returns:
            Report dict with archived count and details
        """
        suspended = self.storage.threads.get_suspended()
        now = datetime.now()

        archived = []
        errors = []

        for thread in suspended:
            hours_since = (now - thread.last_active).total_seconds() / 3600

            if hours_since < self.ARCHIVE_AFTER_HOURS:
                continue

            try:
                result = self.archive_thread(thread)
                if result:
                    archived.append(result)
            except Exception as e:
                logger.error(f"Failed to archive thread {thread.id}: {e}")
                errors.append({"thread_id": thread.id, "error": str(e)})

        report = {
            "archived_count": len(archived),
            "errors": len(errors),
            "archives": archived
        }

        if archived:
            logger.info(f"Archived {len(archived)} stale threads")

        return report

    def archive_thread(self, thread: Thread) -> Optional[dict]:
        """
        Archive a single thread with LLM synthesis.

        Args:
            thread: Thread to archive

        Returns:
            Archive record dict, or None if failed
        """
        # 1. Gather related threads (children)
        related_threads = self._gather_related(thread)

        # 2. Generate LLM synthesis
        synthesis = self._generate_synthesis(thread, related_threads)

        # 3. Index connected bridges
        bridge_index = self._index_bridges(thread)

        # 4. Build archive record
        archive = self._build_archive_record(thread, related_threads, synthesis, bridge_index)

        # 5. Save archive
        self._save_archive(archive)

        # 6. Delete original thread file from disk
        self._delete_thread_file(thread)

        # 7. Clean up related thread files (children that were also archived/suspended)
        for related in related_threads:
            if related.status in (ThreadStatus.SUSPENDED, ThreadStatus.ARCHIVED):
                self._delete_thread_file(related)

        # 8. Clean up orphan bridges
        self._cleanup_orphan_bridges(thread, related_threads)

        # 9. Clean up shared threads referencing this source thread
        self._cleanup_shared_for_thread(thread, related_threads)

        logger.info(f"Archived thread '{thread.title[:30]}' → {archive['id']}")
        return archive

    def _gather_related(self, thread: Thread) -> List[Thread]:
        """Gather child threads and merged-into threads."""
        related = []

        for child_id in thread.child_ids:
            child = self.storage.threads.get(child_id)
            if child:
                related.append(child)

        return related

    def _generate_synthesis(self, thread: Thread, related: List[Thread]) -> str:
        """
        Generate LLM synthesis of thread content.

        Falls back to heuristic extraction if LLM fails.
        """
        # Build content for synthesis
        content_parts = []
        content_parts.append(f"Thread: {thread.title}")
        content_parts.append(f"Topics: {', '.join(thread.topics[:10])}")

        if thread.summary:
            content_parts.append(f"Summary: {thread.summary}")

        # Include last messages (max 10)
        for msg in thread.messages[-10:]:
            content_parts.append(f"[{msg.source}] {msg.content[:200]}")

        # Include related threads
        for rel in related[:3]:
            content_parts.append(f"\nRelated thread: {rel.title}")
            if rel.summary:
                content_parts.append(f"Summary: {rel.summary}")

        content = "\n".join(content_parts)

        # Try LLM synthesis
        llm_result = self._call_llm_synthesis(content)
        if llm_result:
            return llm_result

        # Fallback: heuristic extraction
        return self._heuristic_synthesis(thread, related)

    def _call_llm_synthesis(self, content: str) -> Optional[str]:
        """Call LLM to generate a condensed synthesis."""
        # Load extraction model from config
        model = None
        try:
            config_path = self.storage.ai_path / "config.json"
            if config_path.exists():
                config = json.loads(config_path.read_text())
                model = config.get("llm", {}).get("extraction_model")
        except Exception:
            pass

        prompt = f"""Generate a concise archive synthesis (3-5 sentences max) of this thread content.
Focus on: key decisions made, important discoveries, unresolved questions.
Output only the synthesis text, no formatting.

Content:
{content[:3000]}"""

        try:
            cmd = ["claude", "-p", prompt, "--output-format", "text"]
            if model:
                cmd.extend(["--model", model])

            env = os.environ.copy()
            env[HOOK_GUARD_ENV] = "1"

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()[:1000]

        except Exception as e:
            logger.debug(f"LLM synthesis failed: {e}")

        return None

    def _heuristic_synthesis(self, thread: Thread, related: List[Thread]) -> str:
        """Fallback heuristic synthesis when LLM is unavailable."""
        parts = []

        if thread.summary:
            parts.append(thread.summary)

        for rel in related[:2]:
            if rel.summary:
                parts.append(rel.summary)

        if not parts:
            parts.append(f"Thread '{thread.title}' with {len(thread.messages)} messages.")
            parts.append(f"Topics: {', '.join(thread.topics[:5])}")

        return " ".join(parts)[:500]

    def _index_bridges(self, thread: Thread) -> List[dict]:
        """Index bridges connected to this thread."""
        bridges = self.storage.bridges.get_connected(thread.id)

        index = []
        for bridge in bridges[:20]:  # Max 20 bridges in index
            # Resolve thread titles for readability
            source_title = self._get_thread_title(bridge.source_id)
            target_title = self._get_thread_title(bridge.target_id)

            index.append({
                "from_topic": source_title,
                "to_topic": target_title,
                "type": bridge.relation_type.value,
                "confidence": round(bridge.confidence, 2)
            })

        return index

    def _get_thread_title(self, thread_id: str) -> str:
        """Get thread title by ID, or return truncated ID if not found."""
        thread = self.storage.threads.get(thread_id)
        if thread:
            return thread.title[:40]
        return thread_id[:12] + "..."

    def _build_archive_record(
        self,
        thread: Thread,
        related: List[Thread],
        synthesis: str,
        bridge_index: List[dict]
    ) -> dict:
        """Build the archive record."""
        # Calculate time period
        all_threads = [thread] + related
        created_dates = [t.created_at for t in all_threads]
        active_dates = [t.last_active for t in all_threads]

        total_messages = sum(len(t.messages) for t in all_threads)

        # Collect all topics
        all_topics = set()
        for t in all_threads:
            all_topics.update(t.topics[:5])

        # Extract key decisions from messages
        decisions = []
        for t in all_threads:
            for msg in t.messages:
                content_lower = msg.content.lower()
                if any(kw in content_lower for kw in ["decided", "decision", "chose", "choisi", "decidé"]):
                    decisions.append(msg.content[:100])
                    if len(decisions) >= 5:
                        break

        return {
            "id": f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            "created_at": datetime.now().isoformat(),
            "source_threads": [t.id for t in all_threads],
            "source_titles": [t.title[:50] for t in all_threads],
            "synthesis": synthesis,
            "key_topics": list(all_topics)[:15],
            "key_decisions": decisions[:5],
            "bridge_index": bridge_index,
            "message_count_total": total_messages,
            "period": {
                "from": min(created_dates).isoformat(),
                "to": max(active_dates).isoformat()
            }
        }

    def _save_archive(self, archive: dict):
        """Save archive record to disk."""
        filepath = self.archives_path / f"{archive['id']}.json"

        temp_path = filepath.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(archive, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            temp_path.rename(filepath)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _delete_thread_file(self, thread: Thread):
        """Delete a thread's JSON file from disk."""
        thread_path = self.storage.ai_path / "db" / "threads" / f"{thread.id}.json"
        if thread_path.exists():
            thread_path.unlink()
            logger.debug(f"Deleted thread file: {thread.id}")

        # Remove from indexes
        self.storage.threads._remove_from_indexes(thread.id)

    def _cleanup_orphan_bridges(self, thread: Thread, related: List[Thread]):
        """Delete bridges whose source or target no longer exists."""
        thread_ids = {thread.id} | {t.id for t in related}

        for tid in thread_ids:
            connected = self.storage.bridges.get_connected(tid)
            for bridge in connected:
                self.storage.bridges.delete(bridge.id)

    def _cleanup_shared_for_thread(self, thread: Thread, related: List[Thread]):
        """
        Archive SharedThreads whose source thread is being archived.

        When a source thread is deleted, any published SharedThread
        referencing it becomes orphaned. This archives and unpublishes them.
        """
        try:
            from ..storage.shared import SharedStorage

            shared_path = self.storage.ai_path / "db" / "shared"
            if not shared_path.exists():
                return

            shared_storage = SharedStorage(shared_path)
            thread_ids = {thread.id} | {t.id for t in related}

            for shared_thread in shared_storage.get_all_published():
                if shared_thread.source_thread_id in thread_ids:
                    shared_thread.archive()
                    shared_storage.save_published(shared_thread)
                    shared_storage.unpublish_from_network(shared_thread.id)
                    logger.debug(f"Archived shared thread {shared_thread.id} (source {shared_thread.source_thread_id} archived)")

        except Exception as e:
            logger.debug(f"Shared cleanup error: {e}")

    def get_archives(self, limit: int = 20) -> List[dict]:
        """Get recent archives."""
        archives = []
        for filepath in sorted(self.archives_path.glob("archive_*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                archives.append(data)
            except Exception:
                continue
        return archives

    def search_archives(self, query: str, limit: int = 5) -> List[dict]:
        """Search archives by keyword in synthesis and topics."""
        query_lower = query.lower()
        matches = []

        for filepath in self.archives_path.glob("archive_*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                searchable = (
                    data.get("synthesis", "").lower()
                    + " ".join(data.get("key_topics", [])).lower()
                    + " ".join(data.get("source_titles", [])).lower()
                )
                if query_lower in searchable:
                    matches.append(data)
            except Exception:
                continue

        return matches[:limit]
