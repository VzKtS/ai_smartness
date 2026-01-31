"""
Memory Retriever - Retrieves relevant context for injection.

This module finds and formats the most relevant memory context
based on the user's current message.

Features:
- Hybrid reactivation using LLM for borderline cases
- Automatic slot liberation when max active threads reached
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Default max active threads (can be overridden by config)
DEFAULT_MAX_ACTIVE_THREADS = 100


class MemoryRetriever:
    """
    Retrieves relevant memory context for prompt injection.

    Responsibilities:
    - Find threads similar to user message
    - Get connected threads via bridges
    - Load user rules
    - Format context string for injection
    - Auto-reactivate suspended threads (with LLM for borderline cases)
    - Manage slot liberation when max active threads reached
    """

    def __init__(self, db_path: Path):
        """
        Initialize memory retriever.

        Args:
            db_path: Path to the database directory (.ai/db)
        """
        self.db_path = db_path
        self.ai_path = db_path.parent
        self.threads_dir = db_path / "threads"
        self.bridges_dir = db_path / "bridges"

        # Lazy load embeddings (expensive)
        self._embeddings = None

        # Lazy load hybrid reactivation decider
        self._decider = None

        # Load max active threads from config
        self._max_active_threads = None

    @property
    def embeddings(self):
        """Lazy load embedding manager."""
        if self._embeddings is None:
            try:
                from ..processing.embeddings import get_embedding_manager
                self._embeddings = get_embedding_manager()
            except ImportError:
                # Fallback for direct script execution
                import sys
                package_dir = Path(__file__).parent.parent
                sys.path.insert(0, str(package_dir.parent))
                from ai_smartness.processing.embeddings import get_embedding_manager
                self._embeddings = get_embedding_manager()
        return self._embeddings

    @property
    def decider(self):
        """Lazy load hybrid reactivation decider."""
        if self._decider is None:
            from .reactivation_decider import HybridReactivationDecider
            self._decider = HybridReactivationDecider()
        return self._decider

    @property
    def max_active_threads(self) -> int:
        """Load max active threads from config."""
        if self._max_active_threads is None:
            config_file = self.ai_path / "config.json"
            if config_file.exists():
                try:
                    config = json.loads(config_file.read_text(encoding='utf-8'))
                    self._max_active_threads = config.get("settings", {}).get(
                        "active_threads_limit", DEFAULT_MAX_ACTIVE_THREADS
                    )
                except Exception:
                    self._max_active_threads = DEFAULT_MAX_ACTIVE_THREADS
            else:
                self._max_active_threads = DEFAULT_MAX_ACTIVE_THREADS
        return self._max_active_threads

    def get_relevant_context(self, user_message: str, max_chars: int = 2000) -> str:
        """
        Get relevant memory context for user message.

        Args:
            user_message: The user's prompt
            max_chars: Maximum characters for the context

        Returns:
            Formatted context string for injection
        """
        try:
            # 1. Find similar threads
            similar_threads = self._find_similar_threads(user_message, limit=5)

            # 2. Get user rules
            user_rules = self._load_user_rules()

            # 3. Build context string
            context = self._build_context_string(similar_threads, user_rules, max_chars)

            logger.info(f"Built context: {len(context)} chars for message: {user_message[:50]}...")

            return context

        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return ""

    def _find_similar_threads(self, message: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find threads similar to the message.

        Uses hybrid approach for reactivation:
        - High similarity (>0.35): Auto-reactivate
        - Borderline (0.15-0.35): Consult LLM
        - Low similarity (<0.15): No reactivation

        Args:
            message: User message
            limit: Maximum threads to return

        Returns:
            List of thread dicts sorted by similarity
        """
        if not self.threads_dir.exists():
            return []

        # Embed the message
        message_embedding = self.embeddings.embed(message[:500])

        # Score active AND suspended threads (suspended need higher similarity)
        scored_threads = []
        active_count = 0

        for thread_file in self.threads_dir.glob("*.json"):
            try:
                thread = json.loads(thread_file.read_text(encoding='utf-8'))

                # Skip archived threads only
                status = thread.get("status", "active")
                if status == "archived":
                    continue

                if status == "active":
                    active_count += 1

                # Get thread embedding
                thread_embedding = thread.get("embedding")
                if not thread_embedding or not any(thread_embedding):
                    # Fallback: embed title + topics
                    thread_text = thread.get("title", "") + " " + " ".join(thread.get("topics", []))
                    thread_embedding = self.embeddings.embed(thread_text)

                # Calculate similarity
                similarity = self.embeddings.similarity(message_embedding, thread_embedding)

                # Apply penalty for suspended threads (prefer active at equal similarity)
                min_threshold = 0.05 if status == "active" else 0.12
                if similarity > min_threshold:
                    # Slight penalty for suspended threads in ranking
                    ranking_score = similarity if status == "active" else similarity * 0.9
                    scored_threads.append({
                        "thread": thread,
                        "similarity": similarity,
                        "ranking_score": ranking_score
                    })

            except Exception as e:
                logger.debug(f"Error processing thread {thread_file}: {e}")
                continue

        # Sort by ranking score (active preferred over suspended at equal similarity)
        scored_threads.sort(key=lambda x: x["ranking_score"], reverse=True)

        # Process threads and handle reactivation with hybrid approach
        result_threads = []
        for item in scored_threads[:limit]:
            thread = item["thread"]
            similarity = item["similarity"]

            # Reactivate suspended threads using hybrid approach
            if thread.get("status") == "suspended" and similarity > 0.15:
                decision = self.decider.decide(message, thread, similarity)

                if decision.should_reactivate:
                    # Check if we need to free a slot
                    if active_count >= self.max_active_threads:
                        suspended = self._suspend_least_important_thread(scored_threads)
                        if suspended:
                            active_count -= 1
                            logger.info(
                                f"Freed slot by suspending: {suspended} "
                                f"(active: {active_count}/{self.max_active_threads})"
                            )
                        else:
                            logger.warning(
                                f"Cannot reactivate '{thread.get('title')}': "
                                f"max active threads reached ({self.max_active_threads})"
                            )
                            result_threads.append(thread)
                            continue

                    # Reactivate the thread
                    self._reactivate_thread(thread)
                    thread["status"] = "active"  # Update in-memory for this response
                    active_count += 1

                    logger.info(
                        f"Reactivated thread: {thread.get('title')[:30]} "
                        f"(sim={similarity:.3f}, llm={decision.used_llm}, "
                        f"reason={decision.reason})"
                    )

            result_threads.append(thread)

        return result_threads

    def _suspend_least_important_thread(
        self,
        scored_threads: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Suspend the least important active thread to free a slot.

        Selection criteria (in order):
        1. Not in scored_threads (not relevant to current message)
        2. Lowest weight
        3. Oldest last_active

        Args:
            scored_threads: Currently relevant threads (to avoid suspending)

        Returns:
            Title of suspended thread, or None if none available
        """
        # Get IDs of currently relevant threads
        relevant_ids = {t["thread"].get("id") for t in scored_threads}

        # Find all active threads not in the relevant set
        candidates = []
        for thread_file in self.threads_dir.glob("*.json"):
            try:
                thread = json.loads(thread_file.read_text(encoding='utf-8'))
                if thread.get("status") != "active":
                    continue
                if thread.get("id") in relevant_ids:
                    continue

                candidates.append({
                    "thread": thread,
                    "file": thread_file,
                    "weight": thread.get("weight", 0.5),
                    "last_active": thread.get("last_active", "")
                })
            except Exception:
                continue

        if not candidates:
            return None

        # Sort by weight ascending, then by last_active ascending (oldest first)
        candidates.sort(key=lambda x: (x["weight"], x["last_active"]))

        # Suspend the least important one
        victim = candidates[0]
        thread = victim["thread"]
        thread_file = victim["file"]

        try:
            thread["status"] = "suspended"
            thread["suspended_at"] = datetime.now().isoformat()
            thread["suspended_reason"] = "slot_liberation"
            thread_file.write_text(
                json.dumps(thread, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            return thread.get("title", "Unknown")[:50]
        except Exception as e:
            logger.error(f"Failed to suspend thread {thread.get('id')}: {e}")
            return None

    def _reactivate_thread(self, thread: Dict[str, Any]) -> None:
        """
        Reactivate a suspended thread by updating its status on disk.

        Args:
            thread: Thread dict to reactivate
        """
        thread_id = thread.get("id")
        if not thread_id:
            return

        thread_file = self.threads_dir / f"{thread_id}.json"
        if not thread_file.exists():
            return

        try:
            # Load current state
            current = json.loads(thread_file.read_text(encoding='utf-8'))

            # Update status and activation count
            current["status"] = "active"
            current["activation_count"] = current.get("activation_count", 0) + 1
            current["last_active"] = datetime.now().isoformat()

            # Track reactivation history
            if "reactivation_history" not in current:
                current["reactivation_history"] = []
            current["reactivation_history"].append({
                "timestamp": datetime.now().isoformat(),
                "from_status": "suspended"
            })

            # Remove suspended_at and suspended_reason if present
            current.pop("suspended_at", None)
            current.pop("suspended_reason", None)

            # Save back
            thread_file.write_text(
                json.dumps(current, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )

        except Exception as e:
            logger.error(f"Failed to reactivate thread {thread_id}: {e}")

    def _get_connected_threads(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Get threads connected via bridges.

        Args:
            thread_id: Source thread ID

        Returns:
            List of connected thread dicts
        """
        if not self.bridges_dir.exists():
            return []

        connected_ids = set()

        # Find bridges where this thread is source or target
        for bridge_file in self.bridges_dir.glob("*.json"):
            try:
                bridge = json.loads(bridge_file.read_text(encoding='utf-8'))

                if bridge.get("source_id") == thread_id:
                    connected_ids.add(bridge.get("target_id"))
                elif bridge.get("target_id") == thread_id:
                    connected_ids.add(bridge.get("source_id"))

            except Exception:
                continue

        # Load the connected threads
        connected_threads = []
        for tid in connected_ids:
            thread_file = self.threads_dir / f"{tid}.json"
            if thread_file.exists():
                try:
                    thread = json.loads(thread_file.read_text(encoding='utf-8'))
                    connected_threads.append(thread)
                except Exception:
                    continue

        return connected_threads[:3]  # Limit to 3 connected threads

    def _load_user_rules(self) -> List[str]:
        """
        Load user-defined rules.

        Returns:
            List of rule strings
        """
        rules_file = self.ai_path / "user_rules.json"

        if not rules_file.exists():
            return []

        try:
            data = json.loads(rules_file.read_text(encoding='utf-8'))
            return data.get("rules", [])
        except Exception as e:
            logger.debug(f"Error loading user rules: {e}")
            return []

    def _build_context_string(
        self,
        threads: List[Dict[str, Any]],
        user_rules: List[str],
        max_chars: int
    ) -> str:
        """
        Build the context string for injection.

        Args:
            threads: List of relevant threads
            user_rules: List of user rules
            max_chars: Maximum characters

        Returns:
            Formatted context string
        """
        if not threads and not user_rules:
            return ""

        parts = ["AI Smartness Memory Context:"]

        # Add current/main thread
        if threads:
            main_thread = threads[0]
            parts.append("")
            parts.append(f"Current thread: \"{main_thread.get('title', 'Unknown')}\"")

            # Add summary if available
            summary = main_thread.get("summary", "")
            if summary:
                parts.append(f"Summary: {summary[:200]}")

            # Add topics
            topics = main_thread.get("topics", [])
            if topics:
                parts.append(f"Topics: {', '.join(topics[:5])}")

        # Add related threads (skip first as it's the main thread)
        if len(threads) > 1:
            parts.append("")
            parts.append("Related threads:")
            for thread in threads[1:4]:  # Max 3 related
                title = thread.get("title", "Unknown")[:50]
                summary = thread.get("summary", "")[:50]
                if summary:
                    parts.append(f"- \"{title}\" - {summary}")
                else:
                    parts.append(f"- \"{title}\"")

        # Add user rules
        if user_rules:
            parts.append("")
            parts.append("User rules:")
            for rule in user_rules[:5]:  # Max 5 rules
                parts.append(f"- {rule}")

        # Join and truncate
        context = "\n".join(parts)

        if len(context) > max_chars:
            context = context[:max_chars - 3] + "..."

        return context


def get_memory_retriever(ai_path: Path) -> MemoryRetriever:
    """
    Factory function to get a MemoryRetriever instance.

    Args:
        ai_path: Path to .ai directory

    Returns:
        MemoryRetriever instance
    """
    db_path = ai_path / "db"
    return MemoryRetriever(db_path)
