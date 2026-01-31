#!/usr/bin/env python3
"""
Inject hook for AI Smartness.

Called by UserPromptSubmit to inject context into user prompts.
Includes anti-autohook guard to prevent infinite loops.

This hook:
1. Receives the user's prompt
2. Detects CLI commands (e.g., "ai status", "ai threads") and executes them
3. Builds context from current state (threads, decisions, reminders)
4. Injects invisible context into the prompt
5. Returns the augmented prompt

CLI Commands (v3.0.0):
- "ai status" - Show memory status
- "ai threads" - List threads
- "ai thread <id>" - Show thread details
- "ai bridges" - List bridges
- "ai search <query>" - Search threads
- "ai health" - System health check
- "ai daemon [status|start|stop]" - Daemon control
- "ai mode [status|light|normal|heavy|max]" - Mode control
- "ai help" - Show help

Usage: python3 inject.py
       Receives JSON via stdin from Claude Code: {"message": "user prompt"}
"""

import sys
import os
import json
import re
import subprocess
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

    Claude Code sends JSON with different keys depending on context:
    - VSCode extension: {"prompt": "user message", "session_id": "...", ...}
    - CLI: {"message": "user message"}

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
                    # VSCode uses "prompt", CLI uses "message"
                    msg = data.get('prompt') or data.get('message', '')
                    return sanitize_unicode(msg)
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
# USER RULES DETECTION
# =============================================================================

# Patterns that indicate a user rule
RULE_PATTERNS = [
    r"rappelle[- ]?toi\s*[:：]\s*(.+)",
    r"n['']oublie pas\s*[:：]\s*(.+)",
    r"toujours\s+(.+)",
    r"jamais\s+(.+)",
    r"règle\s*[:：]\s*(.+)",
    r"rule\s*[:：]\s*(.+)",
    r"remember\s*[:：]\s*(.+)",
    r"don['']t forget\s*[:：]\s*(.+)",
    r"always\s+(.+)",
    r"never\s+(.+)",
    r"regla\s*[:：]\s*(.+)",
    r"recuerda\s*[:：]\s*(.+)",
    r"siempre\s+(.+)",
    r"nunca\s+(.+)",
]


def detect_and_save_user_rule(message: str, ai_path: Path) -> Optional[str]:
    """
    Detect if the message contains a user rule and save it.

    Args:
        message: User message
        ai_path: Path to .ai directory

    Returns:
        The detected rule, or None if no rule found
    """
    message_lower = message.lower().strip()

    for pattern in RULE_PATTERNS:
        match = re.search(pattern, message_lower, re.IGNORECASE)
        if match:
            rule = match.group(1).strip()

            # Clean up the rule
            rule = rule.rstrip('.!?')

            if len(rule) > 10:  # Minimum rule length
                save_user_rule(rule, ai_path)
                return rule

    return None


def save_user_rule(rule: str, ai_path: Path):
    """
    Save a user rule to the rules file.

    Args:
        rule: The rule to save
        ai_path: Path to .ai directory
    """
    rules_file = ai_path / "user_rules.json"

    try:
        # Load existing rules
        if rules_file.exists():
            data = json.loads(rules_file.read_text(encoding='utf-8'))
        else:
            data = {"rules": [], "last_updated": ""}

        # Check if rule already exists (case-insensitive)
        existing_lower = [r.lower() for r in data.get("rules", [])]
        if rule.lower() not in existing_lower:
            data["rules"].append(rule)
            data["last_updated"] = datetime.now().isoformat()

            # Keep only last 20 rules
            data["rules"] = data["rules"][-20:]

            # Save
            rules_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )

            log(f"Saved user rule: {rule[:50]}...")

    except Exception as e:
        log(f"Error saving user rule: {e}")


# =============================================================================
# PROMPT CAPTURE
# =============================================================================

# Minimum length for a prompt to be worth capturing
MIN_PROMPT_LENGTH = 50

# Patterns to skip (acknowledgements, thanks, etc.)
SKIP_PROMPT_PATTERNS = [
    r"^(ok|oui|non|yes|no|d'accord|bien|sure|yep|nope)\.?$",
    r"^[\.!?\s]+$",
    r"^(merci|thanks|gracias|thx)\.?$",
    r"^(go|do it|lance|vas-y|fais-le)\.?$",
]


def should_capture_prompt(message: str) -> bool:
    """
    Check if prompt should be captured for thread processing.

    Filters out short messages and acknowledgements.

    Args:
        message: User message

    Returns:
        True if prompt should be captured
    """
    if len(message) < MIN_PROMPT_LENGTH:
        return False

    message_lower = message.lower().strip()

    for pattern in SKIP_PROMPT_PATTERNS:
        if re.match(pattern, message_lower, re.IGNORECASE):
            return False

    return True


def send_prompt_to_daemon(message: str, ai_path: Path) -> bool:
    """
    Send user prompt to daemon for thread processing.

    Args:
        message: User message
        ai_path: Path to .ai directory

    Returns:
        True if sent successfully
    """
    try:
        package_root = get_package_root()
        sys.path.insert(0, str(package_root.parent))

        from ai_smartness.daemon.client import send_capture_with_retry

        # Send with tool="UserPrompt" (processor defaults to source_type="prompt")
        return send_capture_with_retry(ai_path, {
            "tool": "UserPrompt",
            "content": message
        })

    except ImportError as e:
        log(f"Daemon client import failed: {e}")
        return False
    except Exception as e:
        log(f"Failed to send prompt to daemon: {e}")
        return False


# =============================================================================
# CLI COMMAND INTERCEPTION (v3.0.0)
# =============================================================================

# Pattern to match CLI commands in prompt
CLI_COMMAND_PATTERN = re.compile(
    r'^ai\s+(status|threads?|bridges?|search|reindex|health|daemon|mode|help)(?:\s+(.*))?$',
    re.IGNORECASE
)


def detect_cli_command(message: str) -> Optional[Tuple[str, str]]:
    """
    Detect if the message is a CLI command.

    Args:
        message: User message

    Returns:
        Tuple of (command, args) if CLI command detected, None otherwise
    """
    message_stripped = message.strip()

    match = CLI_COMMAND_PATTERN.match(message_stripped)
    if match:
        command = match.group(1).lower()
        args = match.group(2) or ""
        return (command, args.strip())

    return None


def execute_cli_command(command: str, args: str, ai_path: Path) -> str:
    """
    Execute a CLI command and return the output.

    Args:
        command: CLI command (status, threads, etc.)
        args: Command arguments
        ai_path: Path to .ai directory

    Returns:
        Command output string
    """
    try:
        # Build the command
        package_root = get_package_root()
        cli_script = package_root / "cli" / "main.py"

        if not cli_script.exists():
            return f"Error: CLI script not found at {cli_script}"

        # Build command args
        cmd_args = ["python3", str(cli_script), command]
        if args:
            # Split args but preserve quoted strings
            cmd_args.extend(args.split())

        # Set up environment with correct PYTHONPATH
        env = os.environ.copy()
        parent_path = str(package_root.parent)
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{parent_path}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = parent_path

        # Execute with timeout
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=str(ai_path.parent)  # Run from project root
        )

        output = result.stdout
        if result.stderr:
            output += f"\n{result.stderr}"

        return output.strip() if output else "Command completed (no output)"

    except subprocess.TimeoutExpired:
        return "Error: Command timed out (30s)"
    except Exception as e:
        return f"Error executing command: {e}"


def format_cli_response(command: str, args: str, output: str) -> str:
    """
    Format CLI command output as a system reminder.

    Args:
        command: CLI command
        args: Command arguments
        output: Command output

    Returns:
        Formatted system reminder string
    """
    cmd_str = f"ai {command}"
    if args:
        cmd_str += f" {args}"

    return f"""<system-reminder>
CLI Command: {cmd_str}

{output}
</system-reminder>"""


# =============================================================================
# MEMORY RETRIEVAL
# =============================================================================

def get_memory_context(message: str, db_path: Path) -> str:
    """
    Get memory context using MemoryRetriever.

    Args:
        message: User message
        db_path: Path to database

    Returns:
        Memory context string
    """
    try:
        # Import MemoryRetriever
        package_root = get_package_root()
        sys.path.insert(0, str(package_root.parent))

        from ai_smartness.intelligence.memory_retriever import MemoryRetriever

        ai_path = db_path.parent
        retriever = MemoryRetriever(db_path)

        return retriever.get_relevant_context(message, max_chars=2000)

    except ImportError as e:
        log(f"MemoryRetriever import failed: {e}")
        return ""
    except Exception as e:
        log(f"Memory retrieval error: {e}")
        return ""


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

        # Get database path
        db_path = get_db_path()
        ai_path = db_path.parent

        # =================================================================
        # CLI COMMAND INTERCEPTION (v3.0.0)
        # =================================================================
        # Check if the message is a CLI command (e.g., "ai status")
        cli_cmd = detect_cli_command(message)
        if cli_cmd:
            command, args = cli_cmd
            log(f"[CLI] Detected command: ai {command} {args}")

            # Execute the CLI command
            output = execute_cli_command(command, args, ai_path)

            # Format as system reminder
            cli_response = format_cli_response(command, args, output)

            # Return the CLI response injected into a neutral prompt
            # The user's original "ai X" is replaced with context about the result
            augmented_message = f"{cli_response}\n\nThe user executed a CLI command. Summarize the result above briefly."
            print(json.dumps({"message": augmented_message}))

            log(f"[CLI] Executed: ai {command} {args} ({len(output)} chars)")
            return

        # =================================================================
        # NORMAL PROMPT PROCESSING
        # =================================================================

        # Detect and save any user rules in the message
        detected_rule = detect_and_save_user_rule(message, ai_path)
        if detected_rule:
            log(f"Detected user rule: {detected_rule[:50]}...")

        # Send prompt to daemon for thread capture (non-blocking)
        if should_capture_prompt(message):
            if send_prompt_to_daemon(message, ai_path):
                log(f"[UserPrompt] Sent to daemon: {len(message)} chars")
            else:
                log(f"[UserPrompt] Failed to send to daemon")

        # Build lightweight context (GuardCode reminders)
        lightweight_context = build_lightweight_context(message, db_path)
        lightweight_injection = format_injection(lightweight_context)

        # Get memory context (threads, rules)
        memory_context = get_memory_context(message, db_path)

        # Combine injections
        injections = []

        if memory_context:
            injections.append(f"<system-reminder>\n{memory_context}\n</system-reminder>")

        if lightweight_injection:
            injections.append(lightweight_injection)

        if injections:
            # Log the injection
            total_chars = sum(len(i) for i in injections)
            log(f"Injected: {total_chars} chars ({len(memory_context)} memory) for: {message[:50]}...")

            # Inject at the beginning (invisible to user)
            injection = "\n".join(injections)
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
