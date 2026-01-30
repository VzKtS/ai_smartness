"""
Context Synthesis - Generates summaries at 95% context usage.

When the conversation context reaches 95%, this module:
1. Synthesizes the current state
2. Saves all thread information
3. Prepares for context compaction
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

from ..models.thread import Thread, ThreadStatus
from ..storage.manager import StorageManager
from ..config import Config, load_config


@dataclass
class Synthesis:
    """Result of context synthesis."""
    summary: str
    decisions_made: List[str]
    open_questions: List[str]
    active_threads: List[dict]
    key_insights: List[str]
    generated_at: str

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "summary": self.summary,
            "decisions_made": self.decisions_made,
            "open_questions": self.open_questions,
            "active_threads": self.active_threads,
            "key_insights": self.key_insights,
            "generated_at": self.generated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Synthesis":
        """Create from dictionary."""
        return cls(
            summary=data.get("summary", ""),
            decisions_made=data.get("decisions_made", []),
            open_questions=data.get("open_questions", []),
            active_threads=data.get("active_threads", []),
            key_insights=data.get("key_insights", []),
            generated_at=data.get("generated_at", datetime.now().isoformat())
        )


class ContextSynthesizer:
    """
    Generates context synthesis at 95% capacity.

    Uses LLM to create a comprehensive summary of:
    - Current state of work
    - Decisions made and their rationale
    - Open questions and blockers
    - Key insights discovered
    """

    # Synthesis prompts by language
    SYNTHESIS_PROMPTS = {
        "en": """Synthesize the current session state.

Current Thread: {current_thread}
Topics: {topics}

Recent Messages (last {message_count}):
{messages}

Active Threads: {active_threads}

Generate a synthesis with:
1. SUMMARY: 2-3 sentences about current work state
2. DECISIONS: List of decisions made with brief rationale (max 5)
3. OPEN_QUESTIONS: Unresolved questions or blockers (max 3)
4. KEY_INSIGHTS: Important discoveries or patterns (max 3)

Format as JSON:
{{
    "summary": "...",
    "decisions_made": ["decision 1", "decision 2"],
    "open_questions": ["question 1"],
    "key_insights": ["insight 1"]
}}""",

        "fr": """Synthétisez l'état actuel de la session.

Thread actuel: {current_thread}
Sujets: {topics}

Messages récents (derniers {message_count}):
{messages}

Threads actifs: {active_threads}

Générez une synthèse avec:
1. RÉSUMÉ: 2-3 phrases sur l'état actuel du travail
2. DÉCISIONS: Liste des décisions prises avec justification (max 5)
3. QUESTIONS_OUVERTES: Questions non résolues ou blocages (max 3)
4. INSIGHTS_CLÉS: Découvertes ou patterns importants (max 3)

Format JSON:
{{
    "summary": "...",
    "decisions_made": ["décision 1", "décision 2"],
    "open_questions": ["question 1"],
    "key_insights": ["insight 1"]
}}""",

        "es": """Sintetice el estado actual de la sesión.

Thread actual: {current_thread}
Temas: {topics}

Mensajes recientes (últimos {message_count}):
{messages}

Threads activos: {active_threads}

Genere una síntesis con:
1. RESUMEN: 2-3 oraciones sobre el estado actual del trabajo
2. DECISIONES: Lista de decisiones tomadas con justificación (máx 5)
3. PREGUNTAS_ABIERTAS: Preguntas sin resolver o bloqueos (máx 3)
4. INSIGHTS_CLAVE: Descubrimientos o patrones importantes (máx 3)

Formato JSON:
{{
    "summary": "...",
    "decisions_made": ["decisión 1", "decisión 2"],
    "open_questions": ["pregunta 1"],
    "key_insights": ["insight 1"]
}}"""
    }

    def __init__(
        self,
        storage: StorageManager,
        config: Optional[Config] = None
    ):
        """
        Initialize synthesizer.

        Args:
            storage: StorageManager instance
            config: Configuration (loaded if not provided)
        """
        self.storage = storage
        self.config = config or load_config()

    def synthesize(self) -> Synthesis:
        """
        Generate synthesis of current context.

        Returns:
            Synthesis object with all summary data
        """
        # Gather context data
        current = self.storage.threads.get_current()
        active = self.storage.threads.get_active()

        # Build prompt context
        current_thread = current.title if current else "None"
        topics = current.topics[:5] if current else []

        # Get recent messages
        messages = []
        if current:
            for msg in current.messages[-10:]:
                role = msg.role.upper()
                content = msg.content[:200]
                messages.append(f"[{role}] {content}")

        # Get active thread summaries
        active_summaries = []
        for thread in active[:5]:
            active_summaries.append(f"- {thread.title} ({thread.status.value})")

        # Build prompt
        lang = self.config.language
        prompt_template = self.SYNTHESIS_PROMPTS.get(lang, self.SYNTHESIS_PROMPTS["en"])

        prompt = prompt_template.format(
            current_thread=current_thread,
            topics=", ".join(topics) if topics else "None",
            message_count=len(messages),
            messages="\n".join(messages) if messages else "No messages",
            active_threads="\n".join(active_summaries) if active_summaries else "None"
        )

        # Call LLM
        response = self._call_llm(prompt)

        # Parse response
        synthesis = self._parse_response(response, current, active)

        # Save synthesis
        self._save_synthesis(synthesis)

        return synthesis

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM for synthesis.

        Args:
            prompt: Synthesis prompt

        Returns:
            LLM response string
        """
        try:
            # Build command - only add --model if specified
            cmd = ["claude", "-p", prompt, "--output-format", "text"]
            if self.config.extraction_model:
                cmd.extend(["--model", self.config.extraction_model])

            # CRITICAL: Set guard to prevent hook loops
            env = os.environ.copy()
            env["AI_SMARTNESS_V2_HOOK_RUNNING"] = "1"

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )

            if result.returncode == 0:
                return result.stdout.strip()

        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

        # Fallback: generate basic synthesis
        return self._generate_fallback()

    def _generate_fallback(self) -> str:
        """Generate fallback synthesis without LLM."""
        current = self.storage.threads.get_current()

        summary = "Session in progress."
        if current:
            summary = f"Working on: {current.title}"

        return json.dumps({
            "summary": summary,
            "decisions_made": [],
            "open_questions": [],
            "key_insights": []
        })

    def _parse_response(
        self,
        response: str,
        current: Optional[Thread],
        active: List[Thread]
    ) -> Synthesis:
        """
        Parse LLM response into Synthesis.

        Args:
            response: LLM response string
            current: Current thread
            active: Active threads

        Returns:
            Synthesis object
        """
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)

            # Build active threads data
            active_data = []
            for thread in active[:5]:
                active_data.append({
                    "id": thread.id,
                    "title": thread.title,
                    "status": thread.status.value,
                    "topics": thread.topics[:3]
                })

            return Synthesis(
                summary=data.get("summary", ""),
                decisions_made=data.get("decisions_made", []),
                open_questions=data.get("open_questions", []),
                active_threads=active_data,
                key_insights=data.get("key_insights", []),
                generated_at=datetime.now().isoformat()
            )

        except (json.JSONDecodeError, AttributeError):
            # Fallback
            return Synthesis(
                summary=response[:500] if response else "Synthesis failed",
                decisions_made=[],
                open_questions=[],
                active_threads=[{
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value
                } for t in active[:3]],
                key_insights=[],
                generated_at=datetime.now().isoformat()
            )

    def _save_synthesis(self, synthesis: Synthesis):
        """
        Save synthesis to storage.

        Args:
            synthesis: Synthesis to save
        """
        # Save to synthesis history
        synthesis_path = self.storage.db_path / "synthesis"
        synthesis_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"synthesis_{timestamp}.json"

        synthesis_file = synthesis_path / filename
        synthesis_file.write_text(
            json.dumps(synthesis.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # Also update current thread with synthesis
        current = self.storage.threads.get_current()
        if current:
            current.summary = synthesis.summary
            self.storage.threads.save(current)

    def get_latest_synthesis(self) -> Optional[Synthesis]:
        """
        Get the most recent synthesis.

        Returns:
            Latest Synthesis or None
        """
        synthesis_path = self.storage.db_path / "synthesis"
        if not synthesis_path.exists():
            return None

        synthesis_files = sorted(synthesis_path.glob("synthesis_*.json"), reverse=True)
        if not synthesis_files:
            return None

        try:
            data = json.loads(synthesis_files[0].read_text(encoding="utf-8"))
            return Synthesis.from_dict(data)
        except (json.JSONDecodeError, IOError):
            return None

    def format_for_injection(self, synthesis: Synthesis) -> str:
        """
        Format synthesis for context injection.

        Args:
            synthesis: Synthesis to format

        Returns:
            Formatted string for injection
        """
        lang = self.config.language

        if lang == "fr":
            header = "SYNTHÈSE DE SESSION"
        elif lang == "es":
            header = "SÍNTESIS DE SESIÓN"
        else:
            header = "SESSION SYNTHESIS"

        lines = [f"=== {header} ===", "", synthesis.summary, ""]

        if synthesis.decisions_made:
            decisions_header = {
                "en": "Decisions:",
                "fr": "Décisions:",
                "es": "Decisiones:"
            }
            lines.append(decisions_header.get(lang, decisions_header["en"]))
            for decision in synthesis.decisions_made[:5]:
                lines.append(f"  - {decision}")
            lines.append("")

        if synthesis.open_questions:
            questions_header = {
                "en": "Open Questions:",
                "fr": "Questions ouvertes:",
                "es": "Preguntas abiertas:"
            }
            lines.append(questions_header.get(lang, questions_header["en"]))
            for question in synthesis.open_questions[:3]:
                lines.append(f"  ? {question}")
            lines.append("")

        if synthesis.key_insights:
            insights_header = {
                "en": "Key Insights:",
                "fr": "Insights clés:",
                "es": "Insights clave:"
            }
            lines.append(insights_header.get(lang, insights_header["en"]))
            for insight in synthesis.key_insights[:3]:
                lines.append(f"  * {insight}")

        return "\n".join(lines)
