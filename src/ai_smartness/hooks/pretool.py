#!/usr/bin/env python3
"""
PreToolUse hook for AI Smartness v4.3.

Intercepts tool calls before execution to enable virtual .ai/ paths:
1. Agent Help: Read(".ai/help")
2. Active Recall: Read(".ai/recall/<query>")
3. Merge Threads: Read(".ai/merge/<survivor>/<absorbed>")
4. Split Threads: Read(".ai/split/<thread_id>") + Read(".ai/split/<id>/confirm?...")
5. Unlock Threads: Read(".ai/unlock/<thread_id>")

This hook is called by Claude Code before executing a tool.
For virtual paths, it returns the result via additionalContext.

Usage:
    Configure in Claude Code hooks:
    {
      "hooks": {
        "PreToolUse": [
          {
            "matcher": "Read",
            "hooks": [{"type": "command", "command": "python3 /path/to/pretool.py"}]
          }
        ]
      }
    }
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple


# =============================================================================
# ANTI-AUTOHOOK GUARD
# =============================================================================

HOOK_GUARD_ENV = "AI_SMARTNESS_HOOK_RUNNING"


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


def get_ai_path() -> Path:
    """Get the .ai directory path."""
    project_root = get_project_root()
    if project_root:
        return project_root / ".ai"

    # Fallback to package-local .ai
    ai_path = get_package_root() / ".ai"
    ai_path.mkdir(parents=True, exist_ok=True)
    return ai_path


# =============================================================================
# LOGGING
# =============================================================================

def get_log_path() -> Path:
    """Get the log file path."""
    return get_ai_path() / "pretool.log"


def log(message: str):
    """Write to pretool log."""
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


def get_hook_input_from_stdin() -> dict:
    """
    Get full hook input from stdin.

    Claude Code sends JSON with:
    - session_id, transcript_path, cwd, permission_mode, hook_event_name
    - tool_name, tool_input (for tool hooks)

    Returns:
        Full input dict
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
# VIRTUAL PATH PATTERN (v4.3)
# =============================================================================

# Pattern to match virtual .ai/ paths
# Matches: .ai/help, .ai/recall/<query>, .ai/merge/x/y, .ai/split/x, .ai/unlock/x
VIRTUAL_PATH_PATTERN = re.compile(r'(?:^|/)\.ai/(help|recall|merge|split|unlock)(/.*)?(\?.*)?$')


def detect_virtual_path(file_path: str) -> Optional[str]:
    """
    Detect if the file path is a virtual .ai/ path.

    Args:
        file_path: File path from Read tool

    Returns:
        Virtual path string (e.g., ".ai/recall/query") if matched, None otherwise
    """
    if not file_path:
        return None

    # Find the .ai/ part
    idx = file_path.find('.ai/')
    if idx != -1:
        return file_path[idx:]

    return None


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point for PreToolUse hook."""

    # ANTI-AUTOHOOK GUARD
    if not check_hook_guard():
        # Exit 0 with no output = allow
        return

    set_hook_guard()

    try:
        # Get full hook input from stdin
        hook_input = get_hook_input_from_stdin()

        tool_name = hook_input.get('tool_name', '')
        tool_input = hook_input.get('tool_input', {})
        cwd = hook_input.get('cwd', '')

        # Only process Read tool
        if tool_name != "Read":
            # Exit 0 with no output = allow
            return

        file_path = tool_input.get("file_path", "")

        # Check for virtual .ai/ path (recall, merge, split, unlock)
        virtual_path = detect_virtual_path(file_path)
        if virtual_path:
            # Determine AI path from cwd (project working directory)
            if cwd:
                ai_path = Path(cwd) / ".ai"
            else:
                ai_path = get_ai_path()

            log(f"[VIRTUAL] Detected path: {virtual_path} (cwd={cwd}, ai_path={ai_path})")

            # Skip if no .ai directory
            if not ai_path.exists():
                log(f"[VIRTUAL] No .ai directory at {ai_path}")
                return

            # Import and execute virtual path handler
            try:
                # Add package to path
                package_root = get_package_root()
                sys.path.insert(0, str(package_root.parent))

                from ai_smartness.hooks.recall import handle_virtual_path

                result = handle_virtual_path(virtual_path, ai_path)

                if result is None:
                    log(f"[VIRTUAL] Unknown path: {virtual_path}")
                    return

                log(f"[VIRTUAL] Returned {len(result)} chars for: {virtual_path}")

                # Limit additionalContext to avoid "prompt is too long" error
                MAX_CONTEXT_SIZE = 8000
                if len(result) > MAX_CONTEXT_SIZE:
                    # Truncate with notice
                    truncated = result[:MAX_CONTEXT_SIZE]
                    # Find last complete section (## header)
                    last_section = truncated.rfind('\n## ')
                    if last_section > MAX_CONTEXT_SIZE // 2:
                        truncated = truncated[:last_section]
                    result = truncated + f"\n\n... (truncated, {len(result) - len(truncated)} chars omitted)"
                    log(f"[VIRTUAL] Truncated to {len(result)} chars")

                # Return JSON that allows the Read but injects context
                # VSCode bug: "deny" is ignored, so we use "allow" + additionalContext
                # The Read will fail naturally (file doesn't exist) but context is injected
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "additionalContext": result
                    }
                }
                print(json.dumps(output))
                return

            except ImportError as e:
                log(f"[VIRTUAL] Import error: {e}")
                # Can't redirect, let it fail naturally
                return

            except Exception as e:
                log(f"[VIRTUAL] Error: {e}")
                # Can't redirect, let it fail naturally
                return

        # No interception needed, exit 0 with no output = allow

    except Exception as e:
        log(f"[ERROR] {e}")
        # Exit 0 with no output = allow

    finally:
        clear_hook_guard()


if __name__ == '__main__':
    main()
