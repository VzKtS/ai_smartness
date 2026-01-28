"""
GuardCode Enforcer - Rule enforcement for Claude agent behavior.

Enforces:
- Plan mode for complex tasks
- No quick solutions without considering alternatives
- Present all choices to user
"""

import json
import subprocess
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from ..config import load_config, Config


class RuleType(Enum):
    """Types of GuardCode rules."""
    PLAN_MODE = "plan_mode"
    NO_QUICK_SOLUTIONS = "no_quick_solutions"
    PRESENT_CHOICES = "present_choices"
    CONTEXT_AWARENESS = "context_awareness"


@dataclass
class Reminder:
    """A reminder to inject into the context."""
    rule_type: RuleType
    message: str
    priority: int  # 1 = highest, 3 = lowest
    language: str = "en"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.rule_type.value,
            "message": self.message,
            "priority": self.priority
        }


class Rule:
    """Base class for GuardCode rules."""

    rule_type: RuleType = RuleType.CONTEXT_AWARENESS

    def check(self, context: dict, config: Config) -> Optional[Reminder]:
        """
        Check if this rule should generate a reminder.

        Args:
            context: Current context (prompt, thread info, etc.)
            config: Configuration

        Returns:
            Reminder if triggered, None otherwise
        """
        raise NotImplementedError


class PlanModeRule(Rule):
    """Enforce plan mode for complex tasks."""

    rule_type = RuleType.PLAN_MODE

    # Keywords that suggest complex task (by language)
    COMPLEXITY_KEYWORDS = {
        "en": [
            "implement", "refactor", "redesign", "create", "build",
            "add feature", "new feature", "change", "modify", "update",
            "architecture", "system", "migrate", "integrate", "optimize"
        ],
        "fr": [
            "implémenter", "refactorer", "redesigner", "créer", "construire",
            "ajouter", "nouvelle fonctionnalité", "changer", "modifier",
            "architecture", "système", "migrer", "intégrer", "optimiser"
        ],
        "es": [
            "implementar", "refactorizar", "rediseñar", "crear", "construir",
            "añadir", "nueva funcionalidad", "cambiar", "modificar",
            "arquitectura", "sistema", "migrar", "integrar", "optimizar"
        ]
    }

    REMINDERS = {
        "en": "Complex task detected. Consider using plan mode to design the approach before implementation.",
        "fr": "Tâche complexe détectée. Considérez utiliser le mode plan pour concevoir l'approche avant l'implémentation.",
        "es": "Tarea compleja detectada. Considere usar el modo plan para diseñar el enfoque antes de la implementación."
    }

    def check(self, context: dict, config: Config) -> Optional[Reminder]:
        if not config.enforce_plan_mode:
            return None

        prompt = context.get("prompt", "").lower()
        lang = config.language
        keywords = self.COMPLEXITY_KEYWORDS.get(lang, self.COMPLEXITY_KEYWORDS["en"])

        # Check if prompt suggests complex task
        complexity_score = sum(1 for kw in keywords if kw in prompt)

        if complexity_score >= 2:  # At least 2 complexity indicators
            return Reminder(
                rule_type=self.rule_type,
                message=self.REMINDERS.get(lang, self.REMINDERS["en"]),
                priority=1,
                language=lang
            )

        return None


class NoQuickSolutionsRule(Rule):
    """Warn against quick solutions without alternatives."""

    rule_type = RuleType.NO_QUICK_SOLUTIONS

    QUICK_FIX_KEYWORDS = {
        "en": [
            "quick", "quickly", "fast", "just", "simply", "easy",
            "hack", "workaround", "temporary", "hotfix"
        ],
        "fr": [
            "vite", "rapidement", "rapide", "juste", "simplement", "facile",
            "hack", "contournement", "temporaire", "hotfix"
        ],
        "es": [
            "rápido", "rápidamente", "veloz", "solo", "simplemente", "fácil",
            "hack", "solución temporal", "temporal", "hotfix"
        ]
    }

    REMINDERS = {
        "en": "Consider if this is the best approach. Are there other solutions worth evaluating?",
        "fr": "Considérez si c'est la meilleure approche. Y a-t-il d'autres solutions à évaluer?",
        "es": "Considere si este es el mejor enfoque. ¿Hay otras soluciones que valga la pena evaluar?"
    }

    def check(self, context: dict, config: Config) -> Optional[Reminder]:
        if not config.warn_quick_solutions:
            return None

        prompt = context.get("prompt", "").lower()
        lang = config.language
        keywords = self.QUICK_FIX_KEYWORDS.get(lang, self.QUICK_FIX_KEYWORDS["en"])

        # Check for quick fix indicators
        has_quick_indicator = any(kw in prompt for kw in keywords)

        if has_quick_indicator:
            return Reminder(
                rule_type=self.rule_type,
                message=self.REMINDERS.get(lang, self.REMINDERS["en"]),
                priority=2,
                language=lang
            )

        return None


class PresentChoicesRule(Rule):
    """Ensure all choices are presented to user."""

    rule_type = RuleType.PRESENT_CHOICES

    DECISION_KEYWORDS = {
        "en": [
            "choose", "select", "decide", "pick", "which",
            "should i", "should we", "best way", "approach"
        ],
        "fr": [
            "choisir", "sélectionner", "décider", "lequel", "laquelle",
            "dois-je", "devons-nous", "meilleure façon", "approche"
        ],
        "es": [
            "elegir", "seleccionar", "decidir", "cuál", "cuáles",
            "debo", "debemos", "mejor manera", "enfoque"
        ]
    }

    REMINDERS = {
        "en": "When presenting options, ensure ALL viable choices are shown with their trade-offs.",
        "fr": "Lors de la présentation des options, assurez-vous que TOUS les choix viables sont montrés avec leurs compromis.",
        "es": "Al presentar opciones, asegúrese de que TODAS las opciones viables se muestren con sus compensaciones."
    }

    def check(self, context: dict, config: Config) -> Optional[Reminder]:
        if not config.require_all_choices:
            return None

        prompt = context.get("prompt", "").lower()
        lang = config.language
        keywords = self.DECISION_KEYWORDS.get(lang, self.DECISION_KEYWORDS["en"])

        # Check for decision-making context
        is_decision_context = any(kw in prompt for kw in keywords)

        if is_decision_context:
            return Reminder(
                rule_type=self.rule_type,
                message=self.REMINDERS.get(lang, self.REMINDERS["en"]),
                priority=2,
                language=lang
            )

        return None


class GuardCodeEnforcer:
    """
    Main enforcer that checks all rules.

    Collects reminders from all enabled rules based on context.
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize enforcer.

        Args:
            config: Configuration (loaded if not provided)
        """
        self.config = config or load_config()
        self.rules: List[Rule] = [
            PlanModeRule(),
            NoQuickSolutionsRule(),
            PresentChoicesRule()
        ]

    def check(self, prompt: str, thread_context: Optional[dict] = None) -> List[Reminder]:
        """
        Check all rules and return applicable reminders.

        Args:
            prompt: User prompt
            thread_context: Optional thread context info

        Returns:
            List of reminders to inject, sorted by priority
        """
        context = {
            "prompt": prompt,
            "thread": thread_context or {}
        }

        reminders = []
        for rule in self.rules:
            reminder = rule.check(context, self.config)
            if reminder:
                reminders.append(reminder)

        # Sort by priority (1 = highest)
        reminders.sort(key=lambda r: r.priority)

        return reminders

    def format_reminders(self, reminders: List[Reminder]) -> str:
        """
        Format reminders for injection.

        Args:
            reminders: List of reminders

        Returns:
            Formatted string for injection
        """
        if not reminders:
            return ""

        lines = []
        for reminder in reminders:
            lines.append(f"- {reminder.message}")

        return "\n".join(lines)

    def add_rule(self, rule: Rule):
        """
        Add a custom rule.

        Args:
            rule: Rule to add
        """
        self.rules.append(rule)

    def remove_rule(self, rule_type: RuleType):
        """
        Remove rules of a specific type.

        Args:
            rule_type: Type of rules to remove
        """
        self.rules = [r for r in self.rules if r.rule_type != rule_type]
