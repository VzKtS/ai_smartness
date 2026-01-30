"""
Coherence Analyzer - Fast LLM-based coherence checking.

Uses haiku for quick coherence scoring between context (glob/grep)
and subsequent content (response).

Three-tier decision:
- > 0.6: child thread (strong relationship)
- 0.3-0.6: orphan thread (let gossip handle it)
- < 0.3: forget (noise)
"""

import subprocess
import json
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


# Coherence prompt - designed for fast, binary-ish decisions
COHERENCE_PROMPT = """Compare ces deux contenus et évalue leur cohérence thématique.

CONTEXTE (résultat d'une recherche/listing):
{context}

CONTENU (réponse/analyse qui suit):
{content}

Évalue la cohérence sur une échelle de 0.0 à 1.0:
- 1.0 = Le contenu est une analyse/discussion DIRECTE du contexte
- 0.7 = Le contenu traite du même sujet que le contexte
- 0.4 = Le contenu est vaguement lié au contexte
- 0.1 = Le contenu n'a aucun rapport avec le contexte

Réponds UNIQUEMENT avec un JSON:
{{"coherence": 0.X, "reason": "explication courte"}}"""


def check_coherence(
    context: str,
    content: str,
    claude_cli_path: Optional[str] = None,
    timeout: int = 15
) -> Tuple[float, str]:
    """
    Check coherence between context and content using haiku.

    Args:
        context: The context content (e.g., glob results)
        content: The new content to check (e.g., response)
        claude_cli_path: Path to claude CLI
        timeout: Timeout in seconds

    Returns:
        Tuple of (coherence_score, reason)
        Returns (0.0, "error") on failure
    """
    # Truncate for efficiency
    context_short = context[:1500] if len(context) > 1500 else context
    content_short = content[:1500] if len(content) > 1500 else content

    prompt = COHERENCE_PROMPT.format(
        context=context_short,
        content=content_short
    )

    # Find claude CLI
    if claude_cli_path and Path(claude_cli_path).exists():
        claude_cmd = claude_cli_path
    else:
        claude_cmd = "claude"

    try:
        result = subprocess.run(
            [claude_cmd, "-p", prompt, "--model", "haiku", "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            logger.warning(f"Coherence check failed: {result.stderr}")
            return 0.5, "cli_error"  # Default to orphan on error

        response = result.stdout.strip()

        # Parse JSON response
        try:
            # Find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                coherence = float(data.get("coherence", 0.5))
                reason = data.get("reason", "")

                # Clamp to valid range
                coherence = max(0.0, min(1.0, coherence))

                logger.info(f"Coherence: {coherence:.2f} - {reason}")
                return coherence, reason
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse coherence response: {e}")

        return 0.5, "parse_error"

    except subprocess.TimeoutExpired:
        logger.warning("Coherence check timed out")
        return 0.5, "timeout"
    except Exception as e:
        logger.error(f"Coherence check error: {e}")
        return 0.5, "error"


def decide_thread_action(coherence: float) -> str:
    """
    Decide thread action based on coherence score.

    Args:
        coherence: Score from 0.0 to 1.0

    Returns:
        "child" | "orphan" | "forget"
    """
    if coherence > 0.6:
        return "child"
    elif coherence > 0.3:
        return "orphan"
    else:
        return "forget"


# Context tools that trigger coherence checking
CONTEXT_TOOLS = {"Glob", "Grep"}


def is_context_tool(tool_name: str) -> bool:
    """Check if a tool is a context-setting tool."""
    return tool_name in CONTEXT_TOOLS
