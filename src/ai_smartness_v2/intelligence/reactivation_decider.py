"""
Hybrid Reactivation Decider - Uses LLM for borderline cases.

This module decides whether to reactivate suspended threads
using a combination of embedding similarity and LLM reasoning.

Architecture:
- High similarity (>0.35): Auto-reactivate without LLM
- Borderline (0.15-0.35): Consult LLM Haiku
- Low similarity (<0.15): Don't reactivate
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReactivationDecision:
    """Result of a reactivation decision."""
    should_reactivate: bool
    confidence: float
    reason: str
    used_llm: bool  # Whether LLM was consulted


class HybridReactivationDecider:
    """
    Decides thread reactivation using hybrid approach.

    - High similarity (>0.35): Auto-reactivate without LLM
    - Borderline (0.15-0.35): Consult LLM
    - Low similarity (<0.15): Don't reactivate
    """

    # Thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.35
    BORDERLINE_THRESHOLD = 0.15

    def __init__(self, extractor=None):
        """
        Initialize with optional LLM extractor.

        Args:
            extractor: LLMExtractor instance (lazy loaded if None)
        """
        self._extractor = extractor

    @property
    def extractor(self):
        """Lazy load extractor."""
        if self._extractor is None:
            from ..processing.extractor import LLMExtractor
            self._extractor = LLMExtractor()
        return self._extractor

    def decide(
        self,
        user_message: str,
        thread: Dict[str, Any],
        similarity: float
    ) -> ReactivationDecision:
        """
        Decide whether to reactivate a suspended thread.

        Args:
            user_message: The user's current message
            thread: Thread dict with title, topics, summary
            similarity: Pre-calculated embedding similarity

        Returns:
            ReactivationDecision with should_reactivate, confidence, reason
        """
        thread_title = thread.get("title", "Sans titre")[:30]

        # High confidence: Auto-reactivate
        if similarity > self.HIGH_CONFIDENCE_THRESHOLD:
            logger.info(
                f"REACTIVATE (high sim): '{thread_title}' "
                f"sim={similarity:.3f} > {self.HIGH_CONFIDENCE_THRESHOLD}"
            )
            return ReactivationDecision(
                should_reactivate=True,
                confidence=similarity,
                reason=f"High similarity ({similarity:.2f})",
                used_llm=False
            )

        # Low confidence: Don't reactivate
        if similarity < self.BORDERLINE_THRESHOLD:
            logger.debug(
                f"SKIP (low sim): '{thread_title}' "
                f"sim={similarity:.3f} < {self.BORDERLINE_THRESHOLD}"
            )
            return ReactivationDecision(
                should_reactivate=False,
                confidence=1.0 - similarity,
                reason=f"Low similarity ({similarity:.2f})",
                used_llm=False
            )

        # Borderline: Consult LLM
        logger.info(
            f"BORDERLINE: '{thread_title}' sim={similarity:.3f} - consulting LLM"
        )
        return self._llm_decide(user_message, thread, similarity)

    def _llm_decide(
        self,
        user_message: str,
        thread: Dict[str, Any],
        similarity: float
    ) -> ReactivationDecision:
        """Use LLM to decide borderline cases."""
        prompt = self._build_prompt(user_message, thread)
        thread_title = thread.get("title", "Sans titre")[:30]

        try:
            response = self.extractor._call_llm(prompt)

            # Try to parse JSON response
            try:
                # Find JSON in response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    result = json.loads(response[json_start:json_end])
                else:
                    result = json.loads(response)
            except json.JSONDecodeError:
                # If response is just "true"/"false" or similar
                response_lower = response.lower().strip()
                if "true" in response_lower or "oui" in response_lower:
                    result = {"related": True, "confidence": 0.7, "reason": "LLM affirmatif"}
                elif "false" in response_lower or "non" in response_lower:
                    result = {"related": False, "confidence": 0.7, "reason": "LLM négatif"}
                else:
                    # Can't parse, use fallback
                    logger.warning(f"LLM response not parseable: {response[:100]}")
                    return self._fallback_decision(similarity, thread_title)

            related = result.get("related", False)
            llm_confidence = result.get("confidence", 0.5)
            reason = result.get("reason", "LLM decision")

            # Ensure confidence is a float
            if isinstance(llm_confidence, str):
                try:
                    llm_confidence = float(llm_confidence)
                except ValueError:
                    llm_confidence = 0.5

            # Combine embedding similarity with LLM confidence
            final_confidence = (similarity + llm_confidence) / 2

            logger.info(
                f"LLM decision for '{thread_title}': "
                f"related={related}, llm_conf={llm_confidence:.2f}, "
                f"final_conf={final_confidence:.2f}"
            )

            return ReactivationDecision(
                should_reactivate=related,
                confidence=final_confidence,
                reason=f"LLM: {reason}",
                used_llm=True
            )

        except Exception as e:
            logger.warning(f"LLM decision failed: {e}")
            return self._fallback_decision(similarity, thread_title)

    def _fallback_decision(
        self,
        similarity: float,
        thread_title: str
    ) -> ReactivationDecision:
        """Fallback when LLM fails - use similarity threshold."""
        # Middle of borderline zone
        threshold = (self.HIGH_CONFIDENCE_THRESHOLD + self.BORDERLINE_THRESHOLD) / 2
        should_reactivate = similarity > threshold

        logger.info(
            f"Fallback decision for '{thread_title}': "
            f"sim={similarity:.3f} vs threshold={threshold:.3f} -> "
            f"reactivate={should_reactivate}"
        )

        return ReactivationDecision(
            should_reactivate=should_reactivate,
            confidence=similarity,
            reason=f"Fallback (LLM failed): similarity={similarity:.2f}",
            used_llm=False
        )

    def _build_prompt(self, user_message: str, thread: Dict[str, Any]) -> str:
        """Build the LLM prompt for reactivation decision."""
        title = thread.get("title", "Sans titre")
        topics = thread.get("topics", [])
        topics_str = ", ".join(topics[:5]) if topics else "(aucun)"
        summary = thread.get("summary", "")[:200]

        return f"""Tu détermines si un message utilisateur est lié à un thread de mémoire.

MESSAGE UTILISATEUR:
{user_message[:500]}

THREAD CANDIDAT:
- Titre: {title}
- Topics: {topics_str}
- Résumé: {summary if summary else "(aucun)"}

Le message concerne-t-il ce thread de mémoire?
Considère les relations sémantiques, pas juste les mots exacts.

Réponds UNIQUEMENT en JSON:
{{"related": true/false, "confidence": 0.0-1.0, "reason": "explication courte"}}"""
