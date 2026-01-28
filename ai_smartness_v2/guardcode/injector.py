"""
Context Injector - Builds and injects context into prompts.

Creates invisible context blocks that inform the AI about:
- Current thread state
- Active decisions
- Project constraints
- GuardCode reminders
"""

import json
from typing import List, Optional
from dataclasses import dataclass

from ..config import Config, load_config
from ..storage.manager import StorageManager
from ..intelligence.thread_manager import ThreadManager
from .enforcer import GuardCodeEnforcer, Reminder


@dataclass
class InjectionContext:
    """Context data for injection."""
    current_thread: Optional[dict]
    active_threads: List[dict]
    recent_decisions: List[str]
    project_info: dict
    reminders: List[dict]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "current_thread": self.current_thread,
            "active_threads": self.active_threads,
            "recent_decisions": self.recent_decisions,
            "project": self.project_info,
            "reminders": self.reminders
        }


class ContextInjector:
    """
    Builds and formats context for injection into prompts.

    Creates a minimal, invisible context block that provides
    the AI with awareness of:
    - Current conversation thread
    - Related active threads
    - Recent decisions made
    - GuardCode reminders
    """

    def __init__(
        self,
        storage: StorageManager,
        config: Optional[Config] = None
    ):
        """
        Initialize context injector.

        Args:
            storage: StorageManager instance
            config: Configuration (loaded if not provided)
        """
        self.storage = storage
        self.config = config or load_config()
        self.enforcer = GuardCodeEnforcer(self.config)
        self.thread_manager = ThreadManager(storage)

    def build_context(self, prompt: str) -> InjectionContext:
        """
        Build context for injection based on prompt and state.

        Args:
            prompt: User prompt

        Returns:
            InjectionContext with all relevant data
        """
        # Get current thread
        current = self.storage.threads.get_current()
        current_data = None
        if current:
            current_data = {
                "id": current.id,
                "title": current.title,
                "topics": current.topics[:5],
                "message_count": len(current.messages),
                "status": current.status.value
            }

        # Get active threads (top 3 by weight)
        active = self.storage.threads.get_active()
        active.sort(key=lambda t: t.weight, reverse=True)
        active_data = []
        for thread in active[:3]:
            if not current or thread.id != current.id:
                active_data.append({
                    "id": thread.id,
                    "title": thread.title,
                    "topics": thread.topics[:3],
                    "weight": round(thread.weight, 2)
                })

        # Get recent decisions (from thread messages)
        recent_decisions = []
        if current:
            for msg in reversed(current.messages[-10:]):
                if msg.role == "assistant" and msg.metadata.get("is_decision"):
                    recent_decisions.append(msg.metadata.get("decision_summary", ""))
                    if len(recent_decisions) >= 3:
                        break

        # Project info
        project_info = {
            "name": self.config.project_name,
            "language": self.config.language,
            "mode": self.config.mode
        }

        # Get GuardCode reminders
        thread_context = {"topics": current.topics if current else []}
        reminders = self.enforcer.check(prompt, thread_context)
        reminders_data = [r.to_dict() for r in reminders]

        return InjectionContext(
            current_thread=current_data,
            active_threads=active_data,
            recent_decisions=recent_decisions,
            project_info=project_info,
            reminders=reminders_data
        )

    def build_injection(self, prompt: str, format: str = "comment") -> str:
        """
        Build the complete injection string.

        Args:
            prompt: User prompt
            format: Output format ("comment", "json", "minimal")

        Returns:
            Formatted injection string
        """
        context = self.build_context(prompt)

        if format == "minimal":
            return self._format_minimal(context)
        elif format == "json":
            return self._format_json(context)
        else:
            return self._format_comment(context)

    def _format_comment(self, context: InjectionContext) -> str:
        """Format as HTML comment (invisible in output)."""
        data = context.to_dict()

        # Remove empty fields
        data = {k: v for k, v in data.items() if v}

        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

        return f"<!-- ai_smartness: {json_str} -->"

    def _format_json(self, context: InjectionContext) -> str:
        """Format as raw JSON."""
        return json.dumps(context.to_dict(), ensure_ascii=False, indent=2)

    def _format_minimal(self, context: InjectionContext) -> str:
        """Format as minimal text summary."""
        lines = []

        if context.current_thread:
            lines.append(f"[Thread: {context.current_thread['title']}]")

        if context.reminders:
            for reminder in context.reminders:
                lines.append(f"[!] {reminder['message']}")

        if context.recent_decisions:
            lines.append(f"[Decisions: {', '.join(context.recent_decisions[:2])}]")

        return " ".join(lines) if lines else ""

    def inject_into_prompt(self, prompt: str, position: str = "prefix") -> str:
        """
        Inject context into a prompt.

        Args:
            prompt: Original user prompt
            position: Where to inject ("prefix", "suffix", "wrap")

        Returns:
            Prompt with injected context
        """
        injection = self.build_injection(prompt)

        if not injection:
            return prompt

        if position == "prefix":
            return f"{injection}\n\n{prompt}"
        elif position == "suffix":
            return f"{prompt}\n\n{injection}"
        else:  # wrap
            return f"{injection}\n\n{prompt}\n\n{injection}"

    def get_reminders_text(self, prompt: str) -> str:
        """
        Get just the reminders text for display.

        Args:
            prompt: User prompt

        Returns:
            Formatted reminders text
        """
        reminders = self.enforcer.check(prompt)
        return self.enforcer.format_reminders(reminders)
