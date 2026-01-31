#!/usr/bin/env python3
"""
Compact hook for AI Smartness v2.

Called by PreCompact when context reaches 95% capacity.
Triggers synthesis generation and saves session state.

This hook:
1. Generates a comprehensive synthesis via LLM
2. Saves all active thread states
3. Prepares summary for context continuation
4. Returns synthesis for injection into compacted context

Usage: python3 compact.py
       Receives context info via stdin from Claude Code
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


# =============================================================================
# ANTI-AUTOHOOK GUARD
# =============================================================================

HOOK_GUARD_ENV = "AI_SMARTNESS_V2_HOOK_RUNNING"


def check_hook_guard() -> bool:
    """
    Check if we're already inside a hook.

    Returns:
        True if safe to proceed, False if should exit
    """
    if os.environ.get(HOOK_GUARD_ENV):
        return False
    return True


def set_hook_guard():
    """Set the hook guard to prevent re-entry."""
    os.environ[HOOK_GUARD_ENV] = "1"


def clear_hook_guard():
    """Clear the hook guard."""
    if HOOK_GUARD_ENV in os.environ:
        del os.environ[HOOK_GUARD_ENV]


# =============================================================================
# PATH RESOLUTION
# =============================================================================

def get_package_root() -> Path:
    """Get the ai_smartness package root."""
    return Path(__file__).parent.parent


def get_project_root() -> Optional[Path]:
    """
    Find the project root (directory containing .ai).

    Returns:
        Path to project root, or None if not found
    """
    current = get_package_root().parent

    for parent in [current] + list(current.parents):
        if (parent / ".ai").exists():
            return parent
        if len(parent.parts) <= 1:
            break

    return None


def get_db_path() -> Path:
    """Get the database path."""
    project_root = get_project_root()
    if project_root:
        return project_root / ".ai" / "db"

    return get_package_root() / ".ai" / "db"


# =============================================================================
# LOGGING
# =============================================================================

def get_log_path() -> Path:
    """Get the log file path."""
    project_root = get_project_root()
    if project_root:
        ai_path = project_root / ".ai"
    else:
        ai_path = get_package_root() / ".ai"

    ai_path.mkdir(parents=True, exist_ok=True)
    return ai_path / "compact.log"


def log(message: str):
    """Write to compact log."""
    try:
        log_path = get_log_path()
        with open(log_path, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


# =============================================================================
# INPUT HANDLING
# =============================================================================

def sanitize_unicode(text: str) -> str:
    """Clean invalid Unicode characters."""
    if not text:
        return text

    try:
        encoded = text.encode('utf-8', errors='surrogatepass')
        text = encoded.decode('utf-8', errors='replace')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    text = re.sub(r'[\ud800-\udfff]', '', text)
    text = text.replace('\ufffd', '')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return text


def get_context_from_stdin() -> dict:
    """
    Get context info from stdin.

    Returns:
        Context dictionary
    """
    try:
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read()
            if stdin_data:
                stdin_data = sanitize_unicode(stdin_data)
                try:
                    return json.loads(stdin_data)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    return {}


# =============================================================================
# LIGHTWEIGHT SYNTHESIS (without heavy imports)
# =============================================================================

def load_config(db_path: Path) -> dict:
    """Load configuration."""
    config_path = db_path.parent / "config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def get_active_threads(db_path: Path) -> list:
    """Get list of active threads."""
    threads_dir = db_path / "threads"
    if not threads_dir.exists():
        return []

    threads = []
    for tf in threads_dir.glob("*.json"):
        try:
            data = json.loads(tf.read_text(encoding='utf-8'))
            if data.get("status") == "active":
                threads.append(data)
        except Exception:
            continue

    # Sort by last_active
    threads.sort(key=lambda t: t.get("last_active", ""), reverse=True)
    return threads


def generate_synthesis_prompt(threads: list, config: dict) -> str:
    """Generate synthesis prompt for LLM."""
    lang = config.get("language", "en")

    # Build threads summary
    thread_summaries = []
    for t in threads[:5]:
        title = t.get("title", "Untitled")[:50]
        topics = ", ".join(t.get("topics", [])[:3])
        msg_count = len(t.get("messages", []))
        thread_summaries.append(f"- {title} ({msg_count} msgs) [{topics}]")

    threads_text = "\n".join(thread_summaries) if thread_summaries else "No active threads"

    # Get recent messages from most active thread
    messages_text = "No recent messages"
    if threads:
        messages = threads[0].get("messages", [])[-5:]
        msg_lines = []
        for m in messages:
            role = m.get("role", "user").upper()[:4]
            content = m.get("content", "")[:150]
            msg_lines.append(f"[{role}] {content}")
        if msg_lines:
            messages_text = "\n".join(msg_lines)

    prompts = {
        "en": f"""Generate a concise session synthesis for context continuation.

Active Threads:
{threads_text}

Recent Activity:
{messages_text}

Create a JSON synthesis:
{{
    "summary": "2-3 sentence summary of current work state",
    "decisions_made": ["key decision 1", "key decision 2"],
    "open_questions": ["unresolved question"],
    "key_insights": ["important discovery"]
}}

Keep it concise - this will be injected into a new context window.""",

        "fr": f"""Générez une synthèse concise de session pour continuation de contexte.

Threads actifs:
{threads_text}

Activité récente:
{messages_text}

Créez une synthèse JSON:
{{
    "summary": "Résumé en 2-3 phrases de l'état actuel",
    "decisions_made": ["décision clé 1", "décision clé 2"],
    "open_questions": ["question non résolue"],
    "key_insights": ["découverte importante"]
}}

Gardez concis - sera injecté dans une nouvelle fenêtre de contexte.""",

        "es": f"""Genere una síntesis concisa de sesión para continuación de contexto.

Threads activos:
{threads_text}

Actividad reciente:
{messages_text}

Cree una síntesis JSON:
{{
    "summary": "Resumen de 2-3 oraciones del estado actual",
    "decisions_made": ["decisión clave 1", "decisión clave 2"],
    "open_questions": ["pregunta sin resolver"],
    "key_insights": ["descubrimiento importante"]
}}

Mantenga conciso - se inyectará en una nueva ventana de contexto."""
    }

    return prompts.get(lang, prompts["en"])


def call_llm_synthesis(prompt: str, config: dict) -> Optional[str]:
    """Call LLM for synthesis generation."""
    import subprocess

    model = config.get("llm", {}).get("extraction_model")

    try:
        # Build command - only add --model if specified
        cmd = ["claude", "-p", prompt, "--output-format", "text"]
        if model:
            cmd.extend(["--model", model])

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

    except Exception as e:
        log(f"LLM call failed: {e}")

    return None


def parse_synthesis(response: str) -> dict:
    """Parse LLM response into synthesis dict."""
    if not response:
        return {}

    try:
        # Try to extract JSON
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return json.loads(response)

    except json.JSONDecodeError:
        # Return raw as summary
        return {
            "summary": response[:500],
            "decisions_made": [],
            "open_questions": [],
            "key_insights": []
        }


def save_synthesis(synthesis: dict, db_path: Path):
    """Save synthesis to file."""
    synthesis_dir = db_path / "synthesis"
    synthesis_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"synthesis_{timestamp}.json"

    synthesis["generated_at"] = datetime.now().isoformat()

    filepath = synthesis_dir / filename
    filepath.write_text(
        json.dumps(synthesis, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    log(f"Synthesis saved: {filename}")


def format_synthesis_for_injection(synthesis: dict, config: dict) -> str:
    """Format synthesis for context injection."""
    lang = config.get("language", "en")

    headers = {
        "en": "SESSION CONTINUATION",
        "fr": "CONTINUATION DE SESSION",
        "es": "CONTINUACIÓN DE SESIÓN"
    }

    lines = [
        f"=== {headers.get(lang, headers['en'])} ===",
        "",
        synthesis.get("summary", "No summary available"),
        ""
    ]

    decisions = synthesis.get("decisions_made", [])
    if decisions:
        dec_headers = {"en": "Decisions:", "fr": "Décisions:", "es": "Decisiones:"}
        lines.append(dec_headers.get(lang, dec_headers["en"]))
        for d in decisions[:3]:
            lines.append(f"  - {d}")
        lines.append("")

    questions = synthesis.get("open_questions", [])
    if questions:
        q_headers = {"en": "Open:", "fr": "Ouvert:", "es": "Abierto:"}
        lines.append(q_headers.get(lang, q_headers["en"]))
        for q in questions[:2]:
            lines.append(f"  ? {q}")

    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point for compact hook."""

    # ANTI-AUTOHOOK GUARD
    if not check_hook_guard():
        print(json.dumps({"continue": True}))
        return

    set_hook_guard()

    try:
        log("Compact hook triggered - generating synthesis")

        # Get database path
        db_path = get_db_path()
        db_path.mkdir(parents=True, exist_ok=True)

        # Load config
        config = load_config(db_path)

        # Get active threads
        threads = get_active_threads(db_path)

        if not threads:
            log("No active threads - skipping synthesis")
            print(json.dumps({"continue": True}))
            return

        # Generate synthesis prompt
        prompt = generate_synthesis_prompt(threads, config)

        # Call LLM
        log("Calling LLM for synthesis...")
        response = call_llm_synthesis(prompt, config)

        if response:
            # Parse response
            synthesis = parse_synthesis(response)

            # Add thread info
            synthesis["active_threads"] = [
                {"id": t.get("id", "")[:8], "title": t.get("title", "")[:50]}
                for t in threads[:5]
            ]

            # Save synthesis
            save_synthesis(synthesis, db_path)

            # Format for injection
            injection = format_synthesis_for_injection(synthesis, config)

            log(f"Synthesis complete: {len(injection)} chars")

            # Return synthesis as context to inject
            print(json.dumps({
                "continue": True,
                "synthesis": injection
            }))

        else:
            log("LLM synthesis failed - using fallback")
            # Fallback: just list threads
            fallback = "Active work:\n" + "\n".join(
                f"- {t.get('title', 'Untitled')[:40]}"
                for t in threads[:3]
            )
            print(json.dumps({
                "continue": True,
                "synthesis": fallback
            }))

    except Exception as e:
        log(f"[ERROR] {e}")
        print(json.dumps({"continue": True}))

    finally:
        clear_hook_guard()


if __name__ == '__main__':
    main()
