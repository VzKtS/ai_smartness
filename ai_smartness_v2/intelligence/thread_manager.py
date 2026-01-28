"""
Thread Manager - Thread lifecycle management.

Handles:
- Thread creation/continuation decisions
- Thread activation/suspension/archival
- Weight-based thread management
- Context retrieval
"""

import json
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

from ..models.thread import Thread, ThreadStatus, OriginType
from ..storage.manager import StorageManager
from ..processing.extractor import LLMExtractor, Extraction, extract_title_from_content
from ..processing.embeddings import get_embedding_manager


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
                model=llm_config.get("extraction_model", "claude-haiku-3-5-20250620"),
                claude_cli_path=llm_config.get("claude_cli_path")
            )
        else:
            self.extractor = extractor

        self.embeddings = get_embedding_manager()

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
        file_path: Optional[str] = None
    ) -> Tuple[Thread, Extraction]:
        """
        Process incoming content and update threads.

        Args:
            content: Content to process
            source_type: Type of source (prompt, read, write, task, fetch)
            file_path: Optional file path for file-related sources

        Returns:
            Tuple of (Thread, Extraction)
        """
        # 1. Extract semantic information
        extraction = self.extractor.extract(content, source_type, file_path)

        # 2. Decide action
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

        Uses LLM for complex decisions, heuristics for simple cases.
        """
        current = self.storage.threads.get_current()
        active_threads = self.storage.threads.get_active()

        # Simple case: no active threads
        if not active_threads:
            return ThreadDecision(
                action=ThreadAction.NEW_THREAD,
                thread_id=None,
                reason="No active threads",
                confidence=1.0
            )

        # Check for topic match with current thread
        if current:
            similarity = self._calculate_topic_similarity(extraction, current)
            if similarity > 0.6:
                return ThreadDecision(
                    action=ThreadAction.CONTINUE,
                    thread_id=current.id,
                    reason=f"Topic similarity {similarity:.2f} with current thread",
                    confidence=similarity
                )

        # Check suspended threads for reactivation
        suspended = self.storage.threads.get_suspended()
        for thread in suspended:
            similarity = self._calculate_topic_similarity(extraction, thread)
            if similarity > 0.7:
                return ThreadDecision(
                    action=ThreadAction.REACTIVATE,
                    thread_id=thread.id,
                    reason=f"Topic match {similarity:.2f} with suspended thread",
                    confidence=similarity
                )

        # Check if this is a fork of current thread
        if current and self._is_potential_fork(extraction, current):
            return ThreadDecision(
                action=ThreadAction.FORK,
                thread_id=current.id,
                reason="Subtopic or divergent focus detected",
                confidence=0.7
            )

        # Default: new thread
        return ThreadDecision(
            action=ThreadAction.NEW_THREAD,
            thread_id=current.id if current else None,
            reason="New topic detected",
            confidence=0.8
        )

    def _calculate_topic_similarity(self, extraction: Extraction, thread: Thread) -> float:
        """
        Calculate similarity between extraction and thread topics.

        Uses embedding similarity if available, falls back to keyword overlap.
        """
        # Combine extraction subjects and concepts
        extraction_text = ' '.join(extraction.subjects + extraction.key_concepts)

        # Combine thread topics and summary
        thread_text = ' '.join(thread.topics) + ' ' + thread.title

        if not extraction_text or not thread_text:
            return 0.0

        # Use embeddings
        ext_embedding = self.embeddings.embed(extraction_text)
        thread_embedding = thread.embedding or self.embeddings.embed(thread_text)

        return self.embeddings.similarity(ext_embedding, thread_embedding)

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
            thread = Thread.create(title, OriginType(source_type))
            thread.topics = extraction.subjects + extraction.key_concepts
            thread.add_message(content, "user")
            self.storage.threads.save(thread)
            return thread

        elif decision.action == ThreadAction.CONTINUE:
            # Continue existing thread
            thread = self.storage.threads.get(decision.thread_id)
            if thread:
                thread.add_message(content, "user")
                thread.topics = list(set(thread.topics + extraction.subjects))
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
            thread.add_message(content, "user")

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
                thread.add_message(content, "user")
                thread.topics = list(set(thread.topics + extraction.subjects))
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

    def _enforce_thread_limits(self, max_active: int = 30):
        """
        Enforce limits on active threads.

        Suspends lowest-weight threads when limit exceeded.
        """
        active = self.storage.threads.get_active()

        if len(active) <= max_active:
            return

        # Sort by weight (ascending - lowest first)
        active.sort(key=lambda t: t.weight)

        # Suspend excess threads
        to_suspend = len(active) - max_active
        for thread in active[:to_suspend]:
            thread.suspend("auto_limit")
            self.storage.threads.save(thread)

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
