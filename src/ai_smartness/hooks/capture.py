#!/usr/bin/env python3
"""
Capture hook for AI Smartness.

Called by PostToolUse to capture tool results.
Includes anti-autohook guard to prevent infinite loops.

Usage: python3 capture.py [--tool TOOL_NAME] [--output OUTPUT]
       Or receives JSON via stdin from Claude Code.
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional


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
# NOISE FILTERING (Heuristic, not LLM)
# =============================================================================

def filter_noise(content: str) -> Tuple[str, bool]:
    """
    Pre-filter noise before processing.

    This is HEURISTIC filtering only - pattern-based removal of obvious noise.
    Semantic filtering is done by LLM in Phase 2.

    Args:
        content: Raw content from tool

    Returns:
        (cleaned_content, should_process)
    """
    if not content:
        return content, False

    # 1. Remove IDE tags
    cleaned = re.sub(r'<ide_[^>]*>.*?</ide_[^>]*>', '', content, flags=re.DOTALL)
    cleaned = re.sub(r'<ide_[^>]*>', '', cleaned)

    # 2. Skip pure JSON tool outputs (noise)
    stripped = cleaned.strip()
    json_noise_prefixes = [
        "{'filePath':", '{"filePath":',      # Edit tool
        "{'stdout':", '{"stdout":',           # Bash tool
        "{'newTodos':", '{"newTodos":',       # TodoWrite
        "{'retrieval_status':", '{"retrieval_status":',  # Task output
        "{'oldTodos':", '{"oldTodos":',       # TodoWrite
        "{'continue':", '{"continue":',       # Hook output
    ]
    if any(stripped.startswith(p) for p in json_noise_prefixes):
        return '', False

    # 3. Skip too short content
    cleaned = cleaned.strip()
    if len(cleaned) < 30:
        return cleaned, False

    # 4. Skip content without meaningful words
    if ' ' not in cleaned:
        return cleaned, False

    return cleaned, True


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


# =============================================================================
# DATA RETRIEVAL
# =============================================================================

def get_tool_data_from_stdin() -> Tuple[str, str, Optional[str], Optional[str], Optional[dict]]:
    """
    Get tool data from stdin (Claude Code sends JSON).

    Returns:
        (tool_name, tool_output, file_path, session_id, tool_input)
    """
    try:
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read()
            if stdin_data:
                stdin_data = sanitize_unicode(stdin_data)
                try:
                    data = json.loads(stdin_data)
                    tool_name = sanitize_unicode(data.get('tool_name', ''))

                    tool_response = data.get('tool_response', '')
                    if isinstance(tool_response, dict):
                        tool_output = tool_response.get('content', '') or \
                                     tool_response.get('output', '') or \
                                     str(tool_response)
                    else:
                        tool_output = str(tool_response) if tool_response else ''

                    tool_output = sanitize_unicode(tool_output)

                    # Get tool_input for session tracking (V5.1)
                    tool_input = data.get('tool_input', {})
                    file_path = None
                    if isinstance(tool_input, dict):
                        file_path = tool_input.get('file_path', '')

                    # Get session_id for context tracking
                    session_id = data.get('session_id')

                    return tool_name, tool_output, file_path, session_id, tool_input
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    return '', '', None, None, None


# =============================================================================
# PATH RESOLUTION
# =============================================================================

def get_ai_path() -> Path:
    """
    Get the .ai directory path.

    Looks for .ai in the package directory first,
    then searches upward from current working directory.

    Returns:
        Path to .ai directory
    """
    # First try: package-local .ai
    package_dir = Path(__file__).parent.parent
    ai_path = package_dir / ".ai"
    if ai_path.exists():
        return ai_path

    # Second try: search upward from cwd
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        candidate = parent / ".ai"
        if candidate.exists():
            return candidate
        # Also check for ai_smartness/.ai (underscore prefix folder)
        candidate = parent / "ai_smartness" / ".ai"
        if candidate.exists():
            return candidate

    # Fallback: create in package
    ai_path.mkdir(parents=True, exist_ok=True)
    return ai_path


# =============================================================================
# LOGGING
# =============================================================================

def get_log_path() -> Path:
    """Get the log file path."""
    ai_path = get_ai_path()
    return ai_path / "capture.log"


def log(message: str):
    """Write to capture log."""
    try:
        log_path = get_log_path()
        with open(log_path, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Silent fail for logging


# =============================================================================
# DAEMON CLIENT
# =============================================================================

def send_to_daemon(ai_path: Path, data: dict) -> bool:
    """
    Send capture data to the processor daemon.

    Starts daemon if not running.

    Args:
        ai_path: Path to .ai directory
        data: Capture data

    Returns:
        True if sent successfully
    """
    try:
        from ..daemon.client import send_capture_with_retry
        return send_capture_with_retry(ai_path, data)
    except ImportError:
        # Fallback: try direct import via importlib
        try:
            import sys
            import importlib.util
            package_dir = Path(__file__).parent.parent
            client_path = package_dir / "daemon" / "client.py"

            spec = importlib.util.spec_from_file_location("daemon_client", client_path)
            client_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(client_module)

            return client_module.send_capture_with_retry(ai_path, data)
        except Exception as e:
            log(f"[DAEMON] Import error: {e}")
            return False
    except Exception as e:
        log(f"[DAEMON] Send error: {e}")
        return False


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_capture(tool_name: str, output: str, file_path: Optional[str] = None):
    """
    Process a tool output for capture.

    Sends to the processor daemon for thread management.

    Args:
        tool_name: Name of the tool (Read, Write, Task, etc.)
        output: Tool output content
        file_path: Optional file path for Read/Write tools
    """
    # Filter noise
    cleaned, should_process = filter_noise(output)

    if not should_process:
        log(f"[{tool_name}] Filtered (noise or too short)")
        return

    # Log the capture
    preview = cleaned[:100].replace('\n', ' ')
    log(f"[{tool_name}] Captured: {len(cleaned)} chars - {preview}...")

    # Get AI path
    ai_path = get_ai_path()

    # Send to daemon for processing
    success = send_to_daemon(ai_path, {
        "tool": tool_name,
        "content": cleaned,
        "file_path": file_path
    })

    if success:
        log(f"[{tool_name}] Sent to daemon")
    else:
        log(f"[{tool_name}] Failed to send to daemon")


def update_context_tracking(ai_path: Path, session_id: Optional[str]):
    """
    Update context token tracking in heartbeat.

    Args:
        ai_path: Path to .ai directory
        session_id: Current session ID
    """
    if not session_id:
        return

    try:
        # Try relative import first (when running as module)
        try:
            from ..storage import heartbeat as hb
        except ImportError:
            # Fallback: dynamic import (when running as script)
            import importlib.util
            package_dir = Path(__file__).parent.parent
            hb_path = package_dir / "storage" / "heartbeat.py"
            spec = importlib.util.spec_from_file_location("heartbeat", hb_path)
            hb = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(hb)

        result = hb.update_context_tokens(ai_path, session_id)
        if result:
            if result.get("throttled"):
                # Throttled - don't spam logs
                pass
            else:
                log(f"[CONTEXT] Updated: {result['percent']}% ({result['tokens']} tokens)")
    except Exception as e:
        log(f"[CONTEXT] Update failed: {e}")


def update_session_state(ai_path: Path, tool_name: str, tool_input: dict, tool_output: str):
    """
    V5.1: Update session state for work continuity.

    Tracks:
    - Files modified (Edit, Write)
    - Tool history
    - Last agent action

    Args:
        ai_path: Path to .ai directory
        tool_name: Name of the tool used
        tool_input: Tool input parameters
        tool_output: Tool output/result
    """
    try:
        # Try relative import first (when running as module)
        try:
            from ..models.session import load_session_state, save_session_state
        except ImportError:
            # Fallback: dynamic import (when running as script)
            import importlib.util
            package_dir = Path(__file__).parent.parent
            session_path = package_dir / "models" / "session.py"
            spec = importlib.util.spec_from_file_location("session", session_path)
            session_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(session_mod)
            load_session_state = session_mod.load_session_state
            save_session_state = session_mod.save_session_state

        state = load_session_state(ai_path)

        # Track file modifications
        if tool_name in ["Edit", "Write"]:
            file_path = tool_input.get("file_path", "") if isinstance(tool_input, dict) else ""
            if file_path:
                # Extract a summary of the change
                summary = ""
                if tool_name == "Edit":
                    old_str = tool_input.get("old_string", "")[:50] if isinstance(tool_input, dict) else ""
                    summary = f"Modified: {old_str}..." if old_str else "File edited"
                elif tool_name == "Write":
                    summary = "File written/created"

                state.add_file_modified(file_path, tool_name, summary)
                state.set_agent_action(f"{tool_name}: {Path(file_path).name}")

        # Track tool call
        target = ""
        if isinstance(tool_input, dict):
            target = tool_input.get("file_path", "") or \
                     tool_input.get("command", "")[:50] or \
                     tool_input.get("pattern", "") or \
                     tool_input.get("query", "")[:50] or \
                     ""
        if isinstance(target, str) and len(target) > 50:
            target = target[:50] + "..."

        state.add_tool_call(tool_name, target)

        # Save updated state
        save_session_state(ai_path, state)
        log(f"[SESSION] Updated: {tool_name} -> {target[:30] if target else 'N/A'}")

    except Exception as e:
        log(f"[SESSION] Update failed: {e}")


def main():
    """Main entry point for capture hook."""

    # ANTI-AUTOHOOK GUARD
    if not check_hook_guard():
        # Already in a hook, exit silently
        print(json.dumps({"continue": True}))
        return

    set_hook_guard()

    try:
        # Parse arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--tool', default='')
        parser.add_argument('--output', default='')
        args = parser.parse_args()

        # Get data from stdin if not provided
        stdin_file_path = None
        session_id = None
        tool_input = None
        if not args.tool:
            stdin_tool, stdin_output, stdin_file_path, session_id, tool_input = get_tool_data_from_stdin()
            if stdin_tool:
                args.tool = stdin_tool
            if stdin_output:
                args.output = stdin_output

        # Skip only pure interaction tools (no useful content)
        skip_tools = ['AskUserQuestion']
        if args.tool in skip_tools:
            print(json.dumps({"continue": True}))
            return

        # Get AI path
        ai_path = get_ai_path()

        # V5.1: Update session state for work continuity
        if args.tool and tool_input is not None:
            update_session_state(ai_path, args.tool, tool_input, args.output)

        # Process the capture
        if args.tool and args.output:
            process_capture(args.tool, args.output, stdin_file_path)

        # Update context tracking (every tool call)
        if session_id:
            update_context_tracking(ai_path, session_id)

        # Always continue (hook should not block)
        print(json.dumps({"continue": True}))

    except Exception as e:
        # Log error but don't crash
        log(f"[ERROR] {e}")
        print(json.dumps({"continue": True}))

    finally:
        clear_hook_guard()


if __name__ == '__main__':
    main()
