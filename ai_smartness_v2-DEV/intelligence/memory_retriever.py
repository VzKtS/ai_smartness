"""
Memory Retriever - Retrieves relevant context for injection.

This module finds and formats the most relevant memory context
based on the user's current message.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """
    Retrieves relevant memory context for prompt injection.

    Responsibilities:
    - Find threads similar to user message
    - Get connected threads via bridges
    - Load user rules
    - Format context string for injection
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
                from ai_smartness_v2.processing.embeddings import get_embedding_manager
                self._embeddings = get_embedding_manager()
        return self._embeddings

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

        # Score all active threads
        scored_threads = []

        for thread_file in self.threads_dir.glob("*.json"):
            try:
                thread = json.loads(thread_file.read_text(encoding='utf-8'))

                # Only consider active threads
                if thread.get("status") != "active":
                    continue

                # Get thread embedding
                thread_embedding = thread.get("embedding")
                if not thread_embedding or not any(thread_embedding):
                    # Fallback: embed title + topics
                    thread_text = thread.get("title", "") + " " + " ".join(thread.get("topics", []))
                    thread_embedding = self.embeddings.embed(thread_text)

                # Calculate similarity
                similarity = self.embeddings.similarity(message_embedding, thread_embedding)

                if similarity > 0.05:  # Minimum threshold (TF-IDF has low values)
                    scored_threads.append({
                        "thread": thread,
                        "similarity": similarity
                    })

            except Exception as e:
                logger.debug(f"Error processing thread {thread_file}: {e}")
                continue

        # Sort by similarity and return top matches
        scored_threads.sort(key=lambda x: x["similarity"], reverse=True)

        return [item["thread"] for item in scored_threads[:limit]]

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
