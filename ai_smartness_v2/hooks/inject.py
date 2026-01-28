#!/usr/bin/env python3
"""
Inject hook for AI Smartness v2.

Called by UserPromptSubmit to inject context into user prompts.
Includes anti-autohook guard to prevent infinite loops.

This hook:
1. Receives the user's prompt
2. Builds context from current state (threads, decisions, reminders)
3. Injects invisible context into the prompt
4. Returns the augmented prompt

Usage: python3 inject.py
       Receives JSON via stdin from Claude Code: {"message": "user prompt"}
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
    """Get the .ai_smartness_v2 package root."""
    return Path(__file__).parent.parent


def get_project_root() -> Optional[Path]:
    """
    Find the project root (directory containing .ai).

    Returns:
        Path to project root, or None if not found
    """
    # Start from package root and search upward
    current = get_package_root().parent

    for parent in [current] + list(current.parents):
        if (parent / ".ai").exists():
            return parent
        if len(parent.parts) <= 1:  # Reached filesystem root
            break

    return None


def get_db_path() -> Path:
    """Get the database path."""
    project_root = get_project_root()
    if project_root:
        return project_root / ".ai" / "db"

    # Fallback to package-local .ai
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
    return ai_path / "inject.log"


def log(message: str):
    """Write to inject log."""
    try:
        log_path = get_log_path()
        with open(log_path, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Silent fail for logging


# =============================================================================
# INPUT HANDLING
# =============================================================================

def sanitize_unicode(text: str) -> str:
    """
    Clean invalid Unicode characters.

    Args:
        text: Input text

    Returns:
        Cleaned text safe for JSON
    """
    if not text:
        return text

    # Encode/decode to handle surrogates
    try:
        encoded = text.encode('utf-8', errors='surrogatepass')
        text = encoded.decode('utf-8', errors='replace')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    # Remove orphan surrogates
    text = re.sub(r'[\ud800-\udfff]', '', text)

    # Remove replacement character
    text = text.replace('\ufffd', '')

    # Remove problematic control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return text


def get_message_from_stdin() -> str:
    """
    Get user message from stdin.

    Claude Code sends JSON: {"message": "user prompt"}

    Returns:
        User message string
    """
    try:
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read()
            if stdin_data:
                stdin_data = sanitize_unicode(stdin_data)
                try:
                    data = json.loads(stdin_data)
                    return sanitize_unicode(data.get('message', ''))
                except json.JSONDecodeError:
                    return stdin_data  # Return raw if not JSON
    except Exception:
        pass

    return ''


# =============================================================================
# CONTEXT BUILDING (Lightweight version)
# =============================================================================

def build_lightweight_context(message: str, db_path: Path) -> dict:
    """
    Build context without importing heavy modules.

    This is a lightweight version for the hook.
    Full context building happens in guardcode/injector.py

    Args:
        message: User message
        db_path: Path to database

    Returns:
        Context dictionary
    """
    context = {
        "reminders": [],
        "current_thread": None,
        "active_count": 0
    }

    try:
        # Load config
        config_path = db_path.parent / "config.json"
        config = {}
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding='utf-8'))

        # Check GuardCode rules (simplified version)
        guardcode = config.get("guardcode", {})
        message_lower = message.lower()

        # Plan mode reminder
        if guardcode.get("enforce_plan_mode", True):
            complexity_keywords = [
                "implement", "refactor", "create", "build", "add feature",
                "implémenter", "refactorer", "créer", "construire", "ajouter",
                "implementar", "refactorizar", "crear", "construir", "añadir"
            ]
            if sum(1 for kw in complexity_keywords if kw in message_lower) >= 2:
                lang = config.get("language", "en")
                reminders = {
                    "en": "Complex task - consider plan mode",
                    "fr": "Tâche complexe - considérez le mode plan",
                    "es": "Tarea compleja - considere modo plan"
                }
                context["reminders"].append(reminders.get(lang, reminders["en"]))

        # Quick solution warning
        if guardcode.get("warn_quick_solutions", True):
            quick_keywords = ["quick", "fast", "just", "vite", "rapide", "juste", "rápido"]
            if any(kw in message_lower for kw in quick_keywords):
                lang = config.get("language", "en")
                reminders = {
                    "en": "Consider alternatives before quick fix",
                    "fr": "Considérez les alternatives avant correction rapide",
                    "es": "Considere alternativas antes de arreglo rápido"
                }
                context["reminders"].append(reminders.get(lang, reminders["en"]))

        # Get current thread info (lightweight read)
        threads_dir = db_path / "threads"
        if threads_dir.exists():
            thread_files = list(threads_dir.glob("*.json"))
            context["active_count"] = len(thread_files)

            # Find current/most recent thread
            most_recent = None
            most_recent_time = None

            for tf in thread_files[:10]:  # Limit to 10 for performance
                try:
                    thread_data = json.loads(tf.read_text(encoding='utf-8'))
                    if thread_data.get("status") == "active":
                        last_active = thread_data.get("last_active", "")
                        if not most_recent_time or last_active > most_recent_time:
                            most_recent = thread_data
                            most_recent_time = last_active
                except Exception:
                    continue

            if most_recent:
                context["current_thread"] = {
                    "id": most_recent.get("id", "")[:8],
                    "title": most_recent.get("title", "")[:50],
                    "topics": most_recent.get("topics", [])[:3]
                }

    except Exception as e:
        log(f"Context building error: {e}")

    return context


def format_injection(context: dict) -> str:
    """
    Format context as injection comment.

    Args:
        context: Context dictionary

    Returns:
        HTML comment string for injection
    """
    # Remove empty values
    clean_context = {k: v for k, v in context.items() if v}

    if not clean_context:
        return ""

    json_str = json.dumps(clean_context, ensure_ascii=False, separators=(',', ':'))

    return f"<!-- ai_smartness: {json_str} -->"


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point for inject hook."""

    # ANTI-AUTOHOOK GUARD
    if not check_hook_guard():
        # Already in a hook, pass through unchanged
        message = get_message_from_stdin()
        print(json.dumps({"message": message}))
        return

    set_hook_guard()

    try:
        # Get user message
        message = get_message_from_stdin()

        if not message:
            # No message, pass through
            print(json.dumps({"continue": True}))
            return

        # Build context
        db_path = get_db_path()
        context = build_lightweight_context(message, db_path)

        # Format injection
        injection = format_injection(context)

        if injection:
            # Log the injection
            log(f"Injected: {len(injection)} chars for message: {message[:50]}...")

            # Inject at the beginning (invisible to user)
            augmented_message = f"{injection}\n\n{message}"
            print(json.dumps({"message": augmented_message}))
        else:
            # No injection needed
            print(json.dumps({"message": message}))

    except Exception as e:
        # Log error but don't crash - pass through original
        log(f"[ERROR] {e}")
        message = get_message_from_stdin() if 'message' not in dir() else message
        print(json.dumps({"message": message if message else "", "continue": True}))

    finally:
        clear_hook_guard()


if __name__ == '__main__':
    main()
