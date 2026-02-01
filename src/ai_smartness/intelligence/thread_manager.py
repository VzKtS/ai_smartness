"""
Thread Manager - Thread lifecycle management.

Handles:
- Thread creation/continuation decisions
- Thread activation/suspension/archival
- Weight-based thread management
- Context retrieval
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

from ..models.thread import Thread, ThreadStatus, OriginType
from ..storage.manager import StorageManager
from ..processing.extractor import LLMExtractor, Extraction, extract_title_from_content
from ..processing.embeddings import get_embedding_manager


# Map source_type (from extractor) to OriginType (for thread)
# source_type: "prompt", "read", "write", "task", "fetch", "response", "command"
# OriginType: "prompt", "file_read", "task", "fetch", "split", "reactivation"
SOURCE_TO_ORIGIN = {
    "prompt": OriginType.PROMPT,
    "read": OriginType.FILE_READ,
    "write": OriginType.FILE_READ,
    "task": OriginType.TASK,
    "fetch": OriginType.FETCH,
    "response": OriginType.PROMPT,
    "command": OriginType.PROMPT,  # Bash commands treated as prompt origin
}


class ThreadAction(Enum):
    """Action to take for incoming content."""
    NEW_THREAD = "new_thread"
    CONTINUE = "continue"
    FORK = "fork"
    REACTIVATE = "reactivate"


@dataclass
class ThreadDecision:
    """Decision about how to handle content."""
    action: ThreadAction
    thread_id: Optional[str]  # Thread to continue/fork/reactivate
    reason: str
    confidence: float


class ThreadManager:
    """
    Manages thread lifecycle.

    Core responsibilities:
    - Decide if content starts new thread or continues existing
    - Manage thread weights and suspension
    - Handle thread reactivation
    - Provide context for injection
    """

    def __init__(self, storage: StorageManager, extractor: Optional[LLMExtractor] = None):
        """
        Initialize thread manager.

        Args:
            storage: StorageManager instance
            extractor: LLMExtractor instance (optional, created if not provided)
        """
        self.storage = storage

        # Create extractor with config if not provided
        if extractor is None:
            llm_config = self._load_llm_config()
            self.extractor = LLMExtractor(
                model=llm_config.get("extraction_model"),  # None = use session default
                claude_cli_path=llm_config.get("claude_cli_path")
            )
        else:
            self.extractor = extractor

        self.embeddings = get_embedding_manager()

        # Load thread limits from config
        self.active_threads_limit = self._load_active_threads_limit()

    def _load_active_threads_limit(self) -> int:
        """
        Load active threads limit from config.

        Returns:
            Limit (default 30 if not configured)
        """
        try:
            config_path = self.storage.ai_path / "config.json"
            if config_path.exists():
                config = json.loads(config_path.read_text())
                return config.get("settings", {}).get("active_threads_limit", 30)
        except Exception:
            pass
        return 30

    def _load_llm_config(self) -> dict:
        """
        Load LLM configuration from .ai/config.json.

        Returns:
            LLM config dict (empty if not found)
        """
        try:
            config_path = self.storage.ai_path / "config.json"
            if config_path.exists():
                config = json.loads(config_path.read_text())
                return config.get("llm", {})
        except Exception:
            pass
        return {}

    def process_input(
        self,
        content: str,
        source_type: str = "prompt",
        file_path: Optional[str] = None,
        parent_hint: Optional[str] = None
    ) -> Tuple[Thread, Extraction]:
        """
        Process incoming content and update threads.

        Args:
            content: Content to process
            source_type: Type of source (prompt, read, write, task, fetch)
            file_path: Optional file path for file-related sources
            parent_hint: Optional parent thread ID for forced child linking
                        (from coherence-based context linking)

        Returns:
            Tuple of (Thread, Extraction)
        """
        # 1. Extract semantic information
        extraction = self.extractor.extract(content, source_type, file_path)

        # 2. Decide action (or force FORK if parent_hint provided)
        if parent_hint:
            # Coherence-based child linking - force FORK
            logger.info(f"DECIDE: Forcing FORK (parent_hint={parent_hint[:8]}...)")
            decision = ThreadDecision(
                action=ThreadAction.FORK,
                thread_id=parent_hint,
                reason="Coherence-based child linking",
                confidence=0.8
            )
        else:
            decision = self._decide_action(extraction, content)

        # 3. Execute action
        thread = self._execute_action(decision, content, extraction, source_type)

        # 4. Update embeddings
        self._update_thread_embedding(thread)

        # 5. Check thread limits
        self._enforce_thread_limits()

        return thread, extraction

    def _decide_action(self, extraction: Extraction, content: str) -> ThreadDecision:
        """
        Decide what action to take for this content.

        Searches ALL active threads for best match, not just current.
        Uses lower thresholds (0.35 for active, 0.5 for suspended).
        """
        active_threads = self.storage.threads.get_active()

        logger.info(f"DECIDE: {len(active_threads)} active threads, content={content[:50]}...")

        # Simple case: no active threads
        if not active_threads:
            logger.info("DECIDE: No active threads → NEW_THREAD")
            return ThreadDecision(
                action=ThreadAction.NEW_THREAD,
                thread_id=None,
                reason="No active threads",
                confidence=1.0
            )

        # Search ALL active threads for best match (not just current)
        best_match = None
        best_similarity = 0.0

        for thread in active_threads:
            similarity = self._calculate_similarity(content, extraction, thread)
            if similarity > 0.3:  # Log candidates above noise threshold
                logger.info(f"  SIM: {similarity:.3f} → '{thread.title[:30]}'")
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = thread

        logger.info(f"DECIDE: best_similarity={best_similarity:.3f}, threshold=0.35")

        # Lower threshold: 0.35 for better continuation
        if best_similarity > 0.35 and best_match:
            logger.info(f"DECIDE: CONTINUE → '{best_match.title[:30]}'")
            return ThreadDecision(
                action=ThreadAction.CONTINUE,
                thread_id=best_match.id,
                reason=f"Topic match {best_similarity:.2f} with '{best_match.title[:30]}'",
                confidence=best_similarity
            )

        # Check suspended threads for reactivation (threshold 0.5)
        suspended = self.storage.threads.get_suspended()
        for thread in suspended:
            similarity = self._calculate_similarity(content, extraction, thread)
            if similarity > 0.5:
                logger.info(f"DECIDE: REACTIVATE → '{thread.title[:30]}' (sim={similarity:.3f})")
                return ThreadDecision(
                    action=ThreadAction.REACTIVATE,
                    thread_id=thread.id,
                    reason=f"Reactivate suspended {similarity:.2f}",
                    confidence=similarity
                )

        # Check for fork potential with best match
        if best_match and self._is_potential_fork(extraction, best_match):
            logger.info(f"DECIDE: FORK from '{best_match.title[:30]}'")
            return ThreadDecision(
                action=ThreadAction.FORK,
                thread_id=best_match.id,
                reason="Subtopic or divergent focus detected",
                confidence=0.7
            )

        # Default: new thread
        logger.info(f"DECIDE: NEW_THREAD (best_sim={best_similarity:.3f} < 0.35)")
        return ThreadDecision(
            action=ThreadAction.NEW_THREAD,
            thread_id=None,
            reason="New topic detected",
            confidence=0.8
        )

    def _calculate_similarity(
        self,
        content: str,
        extraction: Extraction,
        thread: Thread
    ) -> float:
        """
        Calculate comprehensive similarity using multiple signals.

        Uses content embedding as primary signal with topic overlap as boost.
        Never returns 0 if content is provided.
        """
        # Signal 1: Embedding similarity (primary - 70% weight)
        # Use raw content for embedding, not just extracted topics
        content_text = content[:500] if content else ''

        # Build thread text from title + topics + recent messages
        thread_parts = [thread.title]
        thread_parts.extend(thread.topics)
        for msg in thread.messages[-3:]:
            thread_parts.append(msg.content[:100])
        thread_text = ' '.join(thread_parts)

        if not content_text:
            return 0.0

        # Calculate embeddings
        content_embedding = self.embeddings.embed(content_text)

        # Use cached thread embedding if available, otherwise calculate
        if thread.embedding is not None:
            thread_embedding = thread.embedding
        else:
            thread_embedding = self.embeddings.embed(thread_text)

        embedding_sim = self.embeddings.similarity(content_embedding, thread_embedding)

        # Signal 2: Topic keyword overlap (secondary - 30% weight)
        topic_sim = 0.0
        exact_match_boost = 0.0

        if extraction.subjects and thread.topics:
            extraction_topics = set(s.lower() for s in extraction.subjects)
            thread_topics = set(t.lower() for t in thread.topics)
            common = extraction_topics & thread_topics

            if extraction_topics:
                topic_sim = len(common) / len(extraction_topics)

            # Boost if exact topic match found
            if common:
                exact_match_boost = 0.15

        # Combine: 70% embedding, 30% topic overlap, + boost for exact match
        combined = 0.7 * embedding_sim + 0.3 * topic_sim + exact_match_boost

        return min(combined, 1.0)  # Cap at 1.0

    def _calculate_topic_similarity(self, extraction: Extraction, thread: Thread) -> float:
        """
        Legacy method for backward compatibility.
        Calls _calculate_similarity with empty content.
        """
        extraction_text = ' '.join(extraction.subjects + extraction.key_concepts)
        return self._calculate_similarity(extraction_text, extraction, thread)

    def _is_potential_fork(self, extraction: Extraction, current: Thread) -> bool:
        """Check if content represents a potential fork."""
        # Check if subjects are related but more specific
        current_topics = set(t.lower() for t in current.topics)
        new_subjects = set(s.lower() for s in extraction.subjects)

        # Some overlap but also new concepts
        overlap = current_topics & new_subjects
        new_only = new_subjects - current_topics

        return len(overlap) > 0 and len(new_only) >= len(overlap)

    def _execute_action(
        self,
        decision: ThreadDecision,
        content: str,
        extraction: Extraction,
        source_type: str
    ) -> Thread:
        """Execute the decided action."""

        if decision.action == ThreadAction.NEW_THREAD:
            # Create new thread - use title (subject-based), not intent (action-based)
            title = extraction.title or extract_title_from_content(content)
            origin = SOURCE_TO_ORIGIN.get(source_type, OriginType.PROMPT)
            thread = Thread.create(title, origin)
            thread.topics = extraction.subjects + extraction.key_concepts
            thread.summary = extraction.summary  # Store the summary
            thread.add_message(content, "user", source_type=source_type)
            self.storage.threads.save(thread)
            return thread

        elif decision.action == ThreadAction.CONTINUE:
            # Continue existing thread
            thread = self.storage.threads.get(decision.thread_id)
            if thread:
                thread.add_message(content, "user", source_type=source_type)
                thread.topics = list(set(thread.topics + extraction.subjects))
                # Update summary: append new info if significant
                if extraction.summary and extraction.summary not in thread.summary:
                    if thread.summary:
                        thread.summary = f"{thread.summary} {extraction.summary}"[:500]
                    else:
                        thread.summary = extraction.summary
                thread.record_drift(source_type)
                self.storage.threads.save(thread)
                return thread
            # Fallback: create new
            return self._execute_action(
                ThreadDecision(ThreadAction.NEW_THREAD, None, "Fallback", 0.5),
                content, extraction, source_type
            )

        elif decision.action == ThreadAction.FORK:
            # Fork from parent thread - use title (subject-based)
            parent = self.storage.threads.get(decision.thread_id)
            title = extraction.title or extract_title_from_content(content)
            thread = Thread.create(title, OriginType.SPLIT, parent_id=decision.thread_id)
            thread.topics = extraction.subjects + extraction.key_concepts
            thread.summary = extraction.summary  # Store the summary

            # Inherit parent's weight (child starts with parent's importance)
            if parent:
                thread.weight = parent.weight

            thread.add_message(content, "user", source_type=source_type)

            if parent:
                parent.add_child(thread.id)
                self.storage.threads.save(parent)

            self.storage.threads.save(thread)
            return thread

        elif decision.action == ThreadAction.REACTIVATE:
            # Reactivate suspended thread
            thread = self.storage.threads.get(decision.thread_id)
            if thread:
                thread.reactivate()
                thread.add_message(content, "user", source_type=source_type)
                thread.topics = list(set(thread.topics + extraction.subjects))
                # Update summary with new context
                if extraction.summary and extraction.summary not in thread.summary:
                    if thread.summary:
                        thread.summary = f"{thread.summary} {extraction.summary}"[:500]
                    else:
                        thread.summary = extraction.summary
                self.storage.threads.save(thread)
                return thread
            # Fallback: create new
            return self._execute_action(
                ThreadDecision(ThreadAction.NEW_THREAD, None, "Fallback", 0.5),
                content, extraction, source_type
            )

        # Should never reach here
        raise ValueError(f"Unknown action: {decision.action}")

    def _update_thread_embedding(self, thread: Thread):
        """Update thread embedding from content."""
        # Combine title, topics, and recent messages
        text_parts = [thread.title]
        text_parts.extend(thread.topics)

        for msg in thread.messages[-5:]:  # Last 5 messages
            text_parts.append(msg.content[:200])

        combined_text = ' '.join(text_parts)
        thread.embedding = self.embeddings.embed(combined_text)
        self.storage.threads.save(thread)

    def _enforce_thread_limits(self, max_active: int = None):
        """
        Enforce limits on active threads.

        Suspends lowest-weight threads when limit exceeded.
        Re-reads config each time to pick up mode changes without daemon restart.
        """
        if max_active is None:
            # Re-read from config each time (allows mode changes without restart)
            max_active = self._load_active_threads_limit()

        active = self.storage.threads.get_active()

        if len(active) <= max_active:
            return

        # Sort by weight (ascending - lowest first)
        active.sort(key=lambda t: t.weight)

        # Suspend excess threads
        to_suspend = len(active) - max_active
        suspended_titles = []
        for thread in active[:to_suspend]:
            suspended_titles.append(thread.title[:30])
            thread.suspend("auto_limit")
            self.storage.threads.save(thread)

        logger.info(f"LIMIT: Suspended {to_suspend} threads (limit={max_active}, was={len(active)}): {suspended_titles}")

    def get_context_for_injection(self, max_threads: int = 3) -> dict:
        """
        Get context data for injection into prompts.

        Args:
            max_threads: Maximum threads to include

        Returns:
            Context dictionary
        """
        current = self.storage.threads.get_current()
        active = self.storage.threads.get_active()

        # Sort active by weight
        active.sort(key=lambda t: t.weight, reverse=True)

        context = {
            "current_thread": None,
            "active_threads": [],
            "total_active": len(active)
        }

        if current:
            context["current_thread"] = {
                "id": current.id,
                "title": current.title,
                "topics": current.topics[:5],
                "message_count": len(current.messages)
            }

        for thread in active[:max_threads]:
            if thread.id != (current.id if current else None):
                context["active_threads"].append({
                    "id": thread.id,
                    "title": thread.title,
                    "topics": thread.topics[:3],
                    "weight": round(thread.weight, 2)
                })

        return context

    def find_related_threads(self, text: str, top_k: int = 5) -> List[Tuple[Thread, float]]:
        """
        Find threads related to given text.

        Args:
            text: Text to find related threads for
            top_k: Number of results

        Returns:
            List of (Thread, similarity) tuples
        """
        query_embedding = self.embeddings.embed(text)

        all_threads = self.storage.threads.get_all()
        candidates = []

        for thread in all_threads:
            if thread.embedding:
                candidates.append((thread.id, thread.embedding))

        results = self.embeddings.find_most_similar(
            query_embedding,
            candidates,
            top_k=top_k,
            threshold=0.3
        )

        return [
            (self.storage.threads.get(tid), sim)
            for tid, sim in results
            if self.storage.threads.get(tid)
        ]

    # ==================== Mode Management ====================

    def get_current_mode(self) -> str:
        """
        Get current mode from config.

        Returns:
            Mode string (light, normal, heavy, max)
        """
        try:
            config_path = self.storage.ai_path / "config.json"
            if config_path.exists():
                config = json.loads(config_path.read_text())
                return config.get("mode", "normal")
        except Exception:
            pass
        return "normal"

    def get_mode_quota(self, mode: str = None) -> int:
        """
        Get thread quota for a mode.

        Args:
            mode: Mode name (uses current if None)

        Returns:
            Thread quota for the mode
        """
        if mode is None:
            mode = self.get_current_mode()

        return Thread.MODE_QUOTAS.get(mode, 50)

    def set_mode(self, mode: str) -> dict:
        """
        Change the operating mode.

        This may suspend threads if new quota is lower.

        Args:
            mode: New mode (light, normal, heavy, max)

        Returns:
            Dict with old_mode, new_mode, suspended_count
        """
        if mode not in Thread.MODE_QUOTAS:
            raise ValueError(f"Invalid mode: {mode}. Must be one of: {list(Thread.MODE_QUOTAS.keys())}")

        old_mode = self.get_current_mode()
        old_quota = self.get_mode_quota(old_mode)
        new_quota = Thread.MODE_QUOTAS[mode]

        # Update config
        try:
            config_path = self.storage.ai_path / "config.json"
            config = {}
            if config_path.exists():
                config = json.loads(config_path.read_text())

            config["mode"] = mode
            config["settings"] = config.get("settings", {})
            config["settings"]["active_threads_limit"] = new_quota

            config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to update config: {e}")

        # Update internal limit
        self.active_threads_limit = new_quota

        # Enforce new quota (may suspend threads)
        suspended_count = 0
        if new_quota < old_quota:
            suspended_count = self.storage.threads.enforce_quota(new_quota)

        return {
            "old_mode": old_mode,
            "new_mode": mode,
            "old_quota": old_quota,
            "new_quota": new_quota,
            "suspended_count": suspended_count
        }

    def prune_threads(self) -> dict:
        """
        Apply decay and suspend threads below threshold.

        Also enforces current mode quota.

        Returns:
            Dict with stats
        """
        mode = self.get_current_mode()
        quota = self.get_mode_quota(mode)

        suspended_count = self.storage.threads.prune_threads(mode_quota=quota)
        stats = self.storage.threads.get_weight_stats()

        return {
            "mode": mode,
            "quota": quota,
            "suspended_count": suspended_count,
            "stats": stats
        }

    def get_mode_status(self) -> dict:
        """
        Get current mode status.

        Returns:
            Dict with mode, quota, active, suspended, available
        """
        mode = self.get_current_mode()
        quota = self.get_mode_quota(mode)
        stats = self.storage.threads.get_weight_stats()

        return {
            "mode": mode,
            "quota": quota,
            "active": stats["active_count"],
            "suspended": stats["suspended_count"],
            "available": max(0, quota - stats["active_count"]),
            "all_modes": Thread.MODE_QUOTAS
        }
