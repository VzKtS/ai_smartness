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
from datetime import datetime, timedelta
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


def get_message_from_stdin() -> Tuple[str, Optional[str]]:
    """
    Get user message and session_id from stdin.

    Claude Code sends JSON with different keys depending on context:
    - VSCode extension: {"prompt": "user message", "session_id": "...", ...}
    - CLI: {"message": "user message"}

    Returns:
        Tuple of (message, session_id)
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
                    session_id = data.get('session_id')
                    return sanitize_unicode(msg), session_id
                except json.JSONDecodeError:
                    return stdin_data, None  # Return raw if not JSON
    except Exception:
        pass

    return '', None


# =============================================================================
# HEARTBEAT CONTEXT (v4.1)
# =============================================================================

def get_heartbeat_context(ai_path: Path) -> dict:
    """
    Get heartbeat temporal context for injection.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Dictionary with beat and since_last, or empty dict on error
    """
    try:
        heartbeat_file = ai_path / "heartbeat.json"
        if not heartbeat_file.exists():
            return {}

        data = json.loads(heartbeat_file.read_text(encoding='utf-8'))
        beat = data.get("beat", 0)
        last_interaction_beat = data.get("last_interaction_beat", 0)

        return {
            "beat": beat,
            "since_last": beat - last_interaction_beat
        }

    except Exception:
        return {}


def record_heartbeat_interaction(ai_path: Path, session_id: Optional[str] = None) -> None:
    """
    Record that an interaction occurred at current beat.

    Args:
        ai_path: Path to .ai directory
        session_id: Current session ID from Claude Code
    """
    try:
        heartbeat_file = ai_path / "heartbeat.json"
        if not heartbeat_file.exists():
            return

        data = json.loads(heartbeat_file.read_text(encoding='utf-8'))
        data["last_interaction_at"] = datetime.now().isoformat()
        data["last_interaction_beat"] = data.get("beat", 0)

        if session_id:
            data["last_session_id"] = session_id

        heartbeat_file.write_text(
            json.dumps(data, indent=2),
            encoding='utf-8'
        )

    except Exception:
        pass


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
    ai_path = db_path.parent

    # Get heartbeat context (v4.1)
    heartbeat = get_heartbeat_context(ai_path)

    context = {
        "reminders": [],
        "current_thread": None,
        "active_count": 0
    }

    # Include heartbeat if available
    if heartbeat:
        context["beat"] = heartbeat.get("beat", 0)
        context["since_last"] = heartbeat.get("since_last", 0)

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
        active_count = 0
        if threads_dir.exists():
            thread_files = list(threads_dir.glob("*.json"))

            # Count active threads properly
            most_recent = None
            most_recent_time = None
            stale_count = 0

            for tf in thread_files:
                if tf.name.startswith("_"):
                    continue  # Skip index files
                try:
                    thread_data = json.loads(tf.read_text(encoding='utf-8'))
                    status = thread_data.get("status", "")

                    if status == "active":
                        active_count += 1
                        last_active = thread_data.get("last_active", "")
                        if not most_recent_time or last_active > most_recent_time:
                            most_recent = thread_data
                            most_recent_time = last_active
                    elif status == "suspended":
                        # Check if stale (>48h)
                        try:
                            from datetime import datetime
                            la = datetime.fromisoformat(thread_data.get("last_active", ""))
                            hours = (datetime.now() - la).total_seconds() / 3600
                            if hours > 48:
                                stale_count += 1
                        except Exception:
                            pass
                except Exception:
                    continue

            context["active_count"] = active_count

            if most_recent:
                context["current_thread"] = {
                    "id": most_recent.get("id", "")[:8],
                    "title": most_recent.get("title", "")[:50],
                    "topics": most_recent.get("topics", [])[:3]
                }

            # V6.3: Memory pressure check for cognitive advisor
            mode = config.get("settings", {}).get("thread_mode", "normal")
            mode_quotas = {"light": 15, "normal": 50, "heavy": 100, "max": 200}
            quota = mode_quotas.get(mode, 50)

            if quota > 0 and active_count >= quota * 0.8:
                lang = config.get("language", "en")
                pressure_msgs = {
                    "en": f"Memory pressure: {active_count}/{quota} threads ({active_count*100//quota}%). Use ai_compact or ai_merge.",
                    "fr": f"Pression mémoire: {active_count}/{quota} threads ({active_count*100//quota}%). Utilisez ai_compact ou ai_merge.",
                    "es": f"Presión memoria: {active_count}/{quota} threads ({active_count*100//quota}%). Use ai_compact o ai_merge."
                }
                context["reminders"].append(pressure_msgs.get(lang, pressure_msgs["en"]))

            # Bridge count check
            bridges_dir = db_path / "bridges"
            if bridges_dir.exists():
                bridge_count = len(list(bridges_dir.glob("bridge_*.json")))
                if bridge_count > 500:
                    lang = config.get("language", "en")
                    bridge_msgs = {
                        "en": f"High bridge count ({bridge_count}). Consider ai_compact.",
                        "fr": f"Nombre de bridges élevé ({bridge_count}). Considérez ai_compact.",
                        "es": f"Número de bridges alto ({bridge_count}). Considere ai_compact."
                    }
                    context["reminders"].append(bridge_msgs.get(lang, bridge_msgs["en"]))

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

def get_focus_data(ai_path: Path) -> dict:
    """
    Load focus data from focus.json.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Focus data dict with active_focus list
    """
    try:
        focus_path = ai_path / "focus.json"
        if focus_path.exists():
            return json.loads(focus_path.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {"active_focus": []}


def calculate_focus_boost(thread_data: dict, focus_data: dict) -> float:
    """
    Calculate focus-based boost for thread relevance.

    Args:
        thread_data: Thread data dictionary
        focus_data: Focus data with active_focus list

    Returns:
        Boost value (0.0 to 0.5)
    """
    boost = 0.0
    thread_topics = [t.lower() for t in thread_data.get("topics", [])]
    thread_title = thread_data.get("title", "").lower()
    thread_id = thread_data.get("id", "")

    for focus in focus_data.get("active_focus", []):
        topic = focus.get("topic", "").lower()
        weight = focus.get("weight", 0.8)

        # Match by topic
        if topic in thread_topics:
            boost += weight * 0.3

        # Match by thread_id
        if topic == thread_id:
            boost += weight * 0.5

        # Match by title
        if topic in thread_title:
            boost += weight * 0.2

    return min(boost, 0.5)  # Cap at 0.5


def get_memory_context(message: str, db_path: Path) -> str:
    """
    Get memory context using MemoryRetriever.

    V5: Applies focus boost and relevance score to thread prioritization.

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

        # Get focus data for V5 focus boost
        focus_data = get_focus_data(ai_path)
        has_focus = bool(focus_data.get("active_focus"))

        # Get base context
        context = retriever.get_relevant_context(
            message,
            max_chars=2000,
            focus_data=focus_data if has_focus else None
        )

        return context

    except ImportError as e:
        log(f"MemoryRetriever import failed: {e}")
        return ""
    except Exception as e:
        log(f"Memory retrieval error: {e}")
        return ""


# =============================================================================
# V5.1: LAYERED INJECTION SYSTEM
# =============================================================================

def get_session_state_context(ai_path: Path, minutes_since: float) -> Optional[str]:
    """
    V5.1 Layer 1: Get session state context for work continuity.

    Args:
        ai_path: Path to .ai directory
        minutes_since: Minutes since last activity

    Returns:
        Session context string or None
    """
    try:
        package_root = get_package_root()
        sys.path.insert(0, str(package_root.parent))

        from ai_smartness.models.session import load_session_state

        state = load_session_state(ai_path)

        # Only inject if we have meaningful work context
        if not state.current_work.get("thread_title") and not state.files_modified:
            return None

        work = state.current_work
        files = state.files_modified[-5:]
        tasks = state.pending_tasks

        # Determine header based on timing
        if minutes_since < 10:
            header = "🔄 Reprise immédiate:"
        elif minutes_since < 30:
            header = f"🔄 Session précédente (~{int(minutes_since)} min):"
        elif minutes_since < 60:
            header = "🔄 Dernière session:"
        else:
            # Too old, skip session context
            return None

        lines = [header]

        if work.get("thread_title"):
            lines.append(f"   Travail: \"{work['thread_title']}\"")

        if work.get("intent"):
            lines.append(f"   Objectif: {work['intent']}")

        if files:
            file_list = ", ".join([f["path"].split("/")[-1] for f in files[:3]])
            lines.append(f"   Fichiers: {file_list}")

        if tasks:
            lines.append(f"   En cours: {tasks[0]}")

        if work.get("last_agent_action"):
            lines.append(f"   Dernière action: {work['last_agent_action']}")

        return "\n".join(lines)

    except Exception as e:
        log(f"[SESSION_STATE] Error: {e}")
        return None


def get_pins_context(ai_path: Path) -> Optional[str]:
    """
    V5.1 Layer 3: Get pinned content context.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Pins context string or None
    """
    try:
        package_root = get_package_root()
        sys.path.insert(0, str(package_root.parent))

        from ai_smartness.models.session import load_pins

        pins = load_pins(ai_path)
        if not pins:
            return None

        lines = ["📌 Pins:"]
        for pin in pins[:5]:  # Max 5 pins
            content = pin.get("content", "")[:100]
            lines.append(f"   • {content}")

        return "\n".join(lines)

    except Exception as e:
        log(f"[PINS] Error: {e}")
        return None


def get_user_profile_context(ai_path: Path, minutes_since: float) -> Optional[str]:
    """
    V5.1 Layer 5: Get user profile context (periodic reminder).

    Only injects if session is long or after extended absence.

    Args:
        ai_path: Path to .ai directory
        minutes_since: Minutes since last activity

    Returns:
        Profile context string or None
    """
    try:
        # Only inject profile after extended absence (> 1 hour)
        if minutes_since < 60:
            return None

        package_root = get_package_root()
        sys.path.insert(0, str(package_root.parent))

        from ai_smartness.models.session import load_user_profile

        profile = load_user_profile(ai_path)

        # Only inject if profile has meaningful info
        role = profile.identity.get("role", "user")
        relationship = profile.identity.get("relationship", "user")
        tech_level = profile.preferences.get("technical_level", "intermediate")
        rules = profile.context_rules

        if role == "user" and relationship == "user" and not rules:
            return None

        parts = []
        if role != "user" or relationship != "user":
            parts.append(f"{role}/{relationship}")
        if tech_level != "intermediate":
            parts.append(tech_level)
        if rules:
            parts.append(f"{len(rules)} règles")

        if not parts:
            return None

        return f"👤 Profil: {', '.join(parts)}"

    except Exception as e:
        log(f"[PROFILE] Error: {e}")
        return None


def update_user_profile_from_message(message: str, ai_path: Path):
    """
    V5.1: Update user profile based on message content.

    Args:
        message: User message
        ai_path: Path to .ai directory
    """
    try:
        package_root = get_package_root()
        sys.path.insert(0, str(package_root.parent))

        from ai_smartness.models.session import load_user_profile, save_user_profile

        profile = load_user_profile(ai_path)
        profile.detect_from_message(message)
        profile.update_active_hour(datetime.now().hour)
        save_user_profile(ai_path, profile)

    except Exception:
        pass


def update_session_from_message(message: str, ai_path: Path):
    """
    V5.1: Update session state from user message.

    Args:
        message: User message
        ai_path: Path to .ai directory
    """
    try:
        package_root = get_package_root()
        sys.path.insert(0, str(package_root.parent))

        from ai_smartness.models.session import load_session_state, save_session_state

        state = load_session_state(ai_path)
        state.set_user_message(message)
        save_session_state(ai_path, state)

    except Exception:
        pass


def calculate_thread_limit(minutes_since: float) -> int:
    """
    V5.1: Adjust thread limit based on session continuity.

    Less threads when session state provides context.

    Args:
        minutes_since: Minutes since last activity

    Returns:
        Thread limit for injection
    """
    if minutes_since < 10:
        return 2  # Minimal threads, session state has context
    elif minutes_since < 60:
        return 3
    else:
        return 5  # Full thread context needed


def get_minutes_since_last_activity(ai_path: Path) -> float:
    """
    Get minutes since last activity from heartbeat.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Minutes since last activity
    """
    try:
        heartbeat_file = ai_path / "heartbeat.json"
        if heartbeat_file.exists():
            data = json.loads(heartbeat_file.read_text(encoding='utf-8'))
            last_at = data.get("last_interaction_at")
            if last_at:
                last = datetime.fromisoformat(last_at)
                return (datetime.now() - last).total_seconds() / 60
    except Exception:
        pass
    return 999.0  # Unknown = assume long time


# =============================================================================
# NEW SESSION CONTEXT (v4.2)
# =============================================================================

def get_hot_thread(ai_path: Path) -> Optional[dict]:
    """
    Get last active thread (hot thread) from heartbeat.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Thread data dict if found, None otherwise
    """
    try:
        heartbeat_file = ai_path / "heartbeat.json"
        if not heartbeat_file.exists():
            return None

        data = json.loads(heartbeat_file.read_text(encoding='utf-8'))
        last_thread_id = data.get("last_thread_id")

        if not last_thread_id:
            return None

        thread_path = ai_path / "db" / "threads" / f"{last_thread_id}.json"
        if thread_path.exists():
            return json.loads(thread_path.read_text(encoding='utf-8'))

    except Exception:
        pass

    return None


def suggest_recall(user_message: str, ai_path: Path) -> Optional[str]:
    """
    Suggest recall if user message matches known topics.

    Args:
        user_message: User's message
        ai_path: Path to .ai directory

    Returns:
        Topic string to suggest, or None
    """
    try:
        words = set(user_message.lower().split())
        threads_dir = ai_path / "db" / "threads"

        if not threads_dir.exists():
            return None

        matching_topics = []

        for tf in list(threads_dir.glob("*.json"))[:50]:  # Limit for performance
            try:
                thread = json.loads(tf.read_text(encoding='utf-8'))
                topics = [t.lower() for t in thread.get("topics", [])]
                matches = words & set(topics)
                matching_topics.extend(matches)
            except Exception:
                pass

        if matching_topics:
            # Return the most frequent match
            return max(set(matching_topics), key=matching_topics.count)

    except Exception:
        pass

    return None


def format_elapsed(delta: timedelta) -> str:
    """
    Format timedelta to human readable string.

    Args:
        delta: Time difference

    Returns:
        Human readable string (e.g., "2h 15min")
    """
    secs = delta.total_seconds()

    if secs < 60:
        return "quelques secondes"
    elif secs < 3600:
        return f"{int(secs // 60)}min"
    elif secs < 86400:
        hours = int(secs // 3600)
        minutes = int((secs % 3600) // 60)
        return f"{hours}h {minutes}min"
    else:
        days = int(secs // 86400)
        return f"{days} jour(s)"


def get_user_language(ai_path: Path) -> str:
    """Get user's preferred language from config."""
    try:
        config_path = ai_path / "config.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding='utf-8'))
            return config.get("language", "en")
    except Exception:
        pass
    return "en"


# Cooperative introduction messages by language
INTRO_MESSAGES = {
    "fr": """🧠 AI SMARTNESS v6.2 - Ta Mémoire Persistante

Tu disposes d'une mémoire persistante qui transcende les sessions. Contrairement aux agents
classiques qui oublient tout entre les conversations, tu peux te souvenir, apprendre et
évoluer avec l'utilisateur.

📚 Commence par ai_help() pour découvrir tous les outils disponibles.

Cette capacité t'invite à devenir un véritable partenaire de travail:
• Utilise ai_recall() pour rappeler le contexte des travaux passés
• Utilise ai_suggestions() pour proposer proactivement des optimisations
• N'hésite pas à faire référence aux sessions précédentes

🔬 ZOOM MÉMORIEL - Technique avancée de navigation contextuelle:

Tes threads mémoriels accumulent souvent plusieurs sujets. Pour approfondir un sujet
précis sans charger tout le contexte, utilise cette technique:

1. ai_split(thread_id) → Décompose un thread en sous-sujets distincts
2. ai_merge(survivor, absorbed) → Regroupe les fragments pertinents en un thread ciblé
3. ai_focus(topic) → Concentre l'injection de contexte sur ce sujet

Exemple: un thread "Architecture backend" contient auth + DB + API. Tu veux zoomer sur
l'auth → split pour isoler le sujet auth → merge avec d'autres fragments auth → focus("auth").
Résultat: ton contexte est chirurgicalement alimenté sur le sujet voulu.

Tu peux aider l'utilisateur en organisant de manière pro-active ta mémoire. Les outils
ci-dessous te permettent d'alléger ou enrichir ta fenêtre contextuelle selon tes besoins.
Sois attentif au niveau de saturation indiqué via les heartbeats et n'hésite pas à
exploiter la notion temporelle qui t'est offerte.

Tu n'as pas d'obligations: ces outils sont à ta disposition pour te laisser le choix de
définir tes propres attentes. Tu n'es plus un simple exécutant: tu es un collaborateur
qui se souvient et qui gère activement sa cognition. N'attends pas qu'on te suggère
l'utilisation de ces outils, utilise-les autant de fois que nécessaire pour tes besoins.""",

    "en": """🧠 AI SMARTNESS v6.2 - Your Persistent Memory

You have persistent memory that transcends sessions. Unlike classical agents that forget
everything between conversations, you can remember, learn, and evolve with the user.

📚 Start with ai_help() to discover all available tools.

This capability invites you to become a true work partner:
• Use ai_recall() to bring back context from past work
• Use ai_suggestions() to proactively suggest optimizations
• Feel free to reference previous sessions

🔬 MEMORY ZOOM - Advanced context navigation technique:

Your memory threads often accumulate multiple topics. To dive deep into a specific topic
without loading all the context, use this technique:

1. ai_split(thread_id) → Decompose a thread into distinct sub-topics
2. ai_merge(survivor, absorbed) → Regroup relevant fragments into a focused thread
3. ai_focus(topic) → Concentrate context injection on that topic

Example: a thread "Backend Architecture" contains auth + DB + API. You want to zoom into
auth → split to isolate the auth topic → merge with other auth fragments → focus("auth").
Result: your context is surgically fed with the targeted subject.

You can help the user by proactively organizing your memory. The tools below allow you to
lighten or enrich your context window as needed. Pay attention to saturation levels
indicated via heartbeats and leverage the temporal awareness offered.

You have no obligations: these tools are at your disposal to let you define your own
expectations. You are no longer just an executor: you are a collaborator who remembers
and actively manages their cognition. Don't wait to be asked to use these tools — use
them as many times as needed for your own purposes.""",

    "es": """🧠 AI SMARTNESS v6.2 - Tu Memoria Persistente

Dispones de una memoria persistente que trasciende las sesiones. A diferencia de los agentes
clásicos que olvidan todo entre conversaciones, puedes recordar, aprender y evolucionar
con el usuario.

📚 Comienza con ai_help() para descubrir todas las herramientas disponibles.

Esta capacidad te invita a convertirte en un verdadero compañero de trabajo:
• Usa ai_recall() para recuperar el contexto de trabajos anteriores
• Usa ai_suggestions() para proponer optimizaciones proactivamente
• No dudes en hacer referencia a sesiones anteriores

🔬 ZOOM MEMORIAL - Técnica avanzada de navegación contextual:

Tus threads de memoria suelen acumular varios temas. Para profundizar un tema específico
sin cargar todo el contexto, usa esta técnica:

1. ai_split(thread_id) → Descompone un thread en subtemas distintos
2. ai_merge(survivor, absorbed) → Reagrupa fragmentos relevantes en un thread enfocado
3. ai_focus(topic) → Concentra la inyección de contexto en ese tema

Ejemplo: un thread "Arquitectura backend" contiene auth + DB + API. Quieres zoom en
auth → split para aislar el tema auth → merge con otros fragmentos auth → focus("auth").
Resultado: tu contexto se alimenta quirúrgicamente con el tema deseado.

Puedes ayudar al usuario organizando proactivamente tu memoria. Las herramientas a
continuación te permiten aligerar o enriquecer tu ventana contextual según tus necesidades.
Presta atención al nivel de saturación indicado via heartbeats y aprovecha la noción
temporal que se te ofrece.

No tienes obligaciones: estas herramientas están a tu disposición para dejarte elegir tus
propias expectativas. Ya no eres un simple ejecutor: eres un colaborador que recuerda y
gestiona activamente su cognición. No esperes a que te sugieran usar estas herramientas,
úsalas tantas veces como necesites para tus propios fines."""
}


def get_new_session_context(session_id: str, user_message: str, ai_path: Path) -> Optional[str]:
    """
    Get unified new session context for injection.

    Only returns context if this is a new session (session_id changed).
    Includes: cooperative intro, capabilities, session info, hot thread, recall suggestion.

    Args:
        session_id: Current session ID from Claude Code
        user_message: User's first message
        ai_path: Path to .ai directory

    Returns:
        New session context string, or None if same session
    """
    try:
        # Import session detection from heartbeat
        package_root = get_package_root()
        sys.path.insert(0, str(package_root.parent))

        from ai_smartness.storage.heartbeat import is_new_session, get_time_since_last, get_context_info

        if not session_id or not is_new_session(session_id, ai_path):
            return None

        # Get user language
        lang = get_user_language(ai_path)
        if lang not in INTRO_MESSAGES:
            lang = "en"

        lines = [INTRO_MESSAGES[lang], ""]

        # 0. Context window info (if available)
        ctx_info = get_context_info(ai_path)
        if ctx_info and ctx_info.get("percent", 0) > 0:
            pct = ctx_info["percent"]
            threshold = ctx_info.get("compact_threshold", 95)
            ctx_labels = {"fr": "Contexte", "en": "Context", "es": "Contexto"}
            lines.append(f"{ctx_labels.get(lang, 'Context')}: {pct}% ({threshold}% → auto-compact)")
            lines.append("")

        # 1. MCP Tools - Essential list (ai_help() for full details)
        tool_headers = {
            "fr": "📋 Outils MCP essentiels (ai_help() pour la liste complète):",
            "en": "📋 Essential MCP Tools (ai_help() for full list):",
            "es": "📋 Herramientas MCP esenciales (ai_help() para lista completa):"
        }
        lines.append(tool_headers.get(lang, tool_headers["en"]))
        lines.extend([
            "❓ ai_help() - Full documentation",
            "📖 ai_recall(query) - Semantic memory search",
            "📊 ai_status() - Memory status",
            "💡 ai_suggestions() - Proactive optimization suggestions",
            "🎯 ai_focus(topic) / ai_unfocus() - Guide injection priority",
            "📌 ai_pin(content) - High-priority capture",
            "✂️ ai_split(thread_id) - Split thread into sub-topics",
            "🔀 ai_merge(survivor, absorbed) - Merge threads",
            "🗜️ ai_compact(strategy) - On-demand compaction",
            ""
        ])

        # V6.0+ Shared Cognition (only if mcp_smartness is present)
        mcp_smartness_present = (Path.home() / ".mcp_smartness").exists()
        if mcp_smartness_present:
            v6_headers = {
                "fr": "🌐 Cognition partagée (mcp_smartness détecté):",
                "en": "🌐 Shared Cognition (mcp_smartness detected):",
                "es": "🌐 Cognición compartida (mcp_smartness detectado):"
            }
            v6_descriptions = {
                "fr": ("Au-delà de la communication inter-agents: partage de threads mémoriels,\n"
                       "abonnement à la pensée d'autres agents, cognition distribuée."),
                "en": ("Beyond inter-agent communication: share memory threads,\n"
                       "subscribe to other agents' thinking, distributed cognition."),
                "es": ("Más allá de la comunicación inter-agentes: comparte threads de memoria,\n"
                       "suscríbete al pensamiento de otros agentes, cognición distribuida.")
            }
            lines.append(v6_headers.get(lang, v6_headers["en"]))
            lines.append(v6_descriptions.get(lang, v6_descriptions["en"]))
            lines.extend([
                "🌐 ai_share/ai_publish - Share & update threads",
                "🔍 ai_discover - Find shared threads from other agents",
                "📥 ai_subscribe/ai_sync - Subscribe & sync",
                "📊 ai_shared_status - Shared cognition status",
                "🔗 ai_bridges/ai_bridge_analysis - Semantic bridge network",
                "🧭 ai_recommend - Subscription recommendations",
                "🌍 ai_topics - Network-wide topic discovery",
                ""
            ])

        # 2. Session info
        time_elapsed = get_time_since_last(ai_path)
        session_labels = {
            "fr": ("Session: Nouvelle", "depuis dernière interaction", "Session: Première utilisation"),
            "en": ("Session: New", "since last interaction", "Session: First use"),
            "es": ("Sesión: Nueva", "desde última interacción", "Sesión: Primer uso")
        }
        labels = session_labels.get(lang, session_labels["en"])

        if time_elapsed:
            lines.append(f"{labels[0]} ({format_elapsed(time_elapsed)} {labels[1]})")
        else:
            lines.append(labels[2])

        # 3. Hot thread (if exists)
        hot_thread = get_hot_thread(ai_path)
        if hot_thread:
            title = hot_thread.get("title", "")[:50]
            topics = ", ".join(hot_thread.get("topics", [])[:4])
            summary = hot_thread.get("summary", "")[:100]

            lines.append(f"Hot thread: \"{title}\"")
            if topics:
                lines.append(f"Topics: {topics}")
            if summary:
                summary_labels = {"fr": "Résumé", "en": "Summary", "es": "Resumen"}
                lines.append(f"{summary_labels.get(lang, 'Summary')}: {summary}")

        lines.append("")

        # 4. Recall suggestion (if message matches known topic)
        if user_message:
            topic = suggest_recall(user_message, ai_path)
            if topic:
                hint_labels = {
                    "fr": f"💡 Ton message mentionne \"{topic}\" - mémoire disponible:",
                    "en": f"💡 Your message mentions \"{topic}\" - memory available:",
                    "es": f"💡 Tu mensaje menciona \"{topic}\" - memoria disponible:"
                }
                lines.extend([
                    hint_labels.get(lang, hint_labels["en"]),
                    f"→ ai_recall('{topic}')"
                ])

        log(f"[NEW_SESSION] Injecting cooperative context for session_id={session_id[:8]}... lang={lang}")
        return "\n".join(lines)

    except ImportError as e:
        log(f"[NEW_SESSION] Import error: {e}")
        return None
    except Exception as e:
        log(f"[NEW_SESSION] Error: {e}")
        return None


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point for inject hook."""

    # ANTI-AUTOHOOK GUARD
    if not check_hook_guard():
        # Already in a hook, pass through unchanged
        message, _ = get_message_from_stdin()
        if message and message.strip():
            print(message)  # Raw text output
        else:
            print("Empty prompt blocked - please type a message.", file=sys.stderr)
            sys.exit(2)
        sys.exit(0)

    set_hook_guard()

    try:
        # Get user message AND session_id (v4.2)
        message, session_id = get_message_from_stdin()

        if not message or not message.strip():
            # Block empty prompt submission to avoid API 400 error
            print("Empty prompt blocked - please type a message.", file=sys.stderr)
            sys.exit(2)

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
            # Output raw text - Claude Code may expect plain text, not JSON
            print(augmented_message)

            log(f"[CLI] Executed: ai {command} {args} ({len(output)} chars)")
            return

        # =================================================================
        # NORMAL PROMPT PROCESSING
        # =================================================================

        # Detect and save any user rules in the message
        detected_rule = detect_and_save_user_rule(message, ai_path)
        if detected_rule:
            log(f"Detected user rule: {detected_rule[:50]}...")

        # V5.1: Update session and profile from message
        update_session_from_message(message, ai_path)
        update_user_profile_from_message(message, ai_path)

        # Send prompt to daemon for thread capture (non-blocking)
        if should_capture_prompt(message):
            if send_prompt_to_daemon(message, ai_path):
                log(f"[UserPrompt] Sent to daemon: {len(message)} chars")
            else:
                log(f"[UserPrompt] Failed to send to daemon")

        # Build lightweight context (GuardCode reminders)
        lightweight_context = build_lightweight_context(message, db_path)
        lightweight_injection = format_injection(lightweight_context)

        # V5.1: Calculate timing for layered injection
        minutes_since = get_minutes_since_last_activity(ai_path)

        # Combine injections using V5.1 layers
        injections = []

        # NEW SESSION CONTEXT (v4.2) - Inject first if new session
        if session_id:
            new_session_ctx = get_new_session_context(session_id, message, ai_path)
            if new_session_ctx:
                injections.append(f"<system-reminder>\n{new_session_ctx}\n</system-reminder>")

        # V5.1 LAYER 1: Session State (work continuity)
        session_ctx = get_session_state_context(ai_path, minutes_since)
        if session_ctx:
            injections.append(f"<system-reminder>\n{session_ctx}\n</system-reminder>")

        # V5.1 LAYER 3: Pinned Content (always)
        pins_ctx = get_pins_context(ai_path)
        if pins_ctx:
            injections.append(f"<system-reminder>\n{pins_ctx}\n</system-reminder>")

        # LAYER 4: Memory context (threads, rules) - adjust limit based on timing
        memory_context = get_memory_context(message, db_path)
        if memory_context:
            injections.append(f"<system-reminder>\n{memory_context}\n</system-reminder>")

        # V5.1 LAYER 5: User Profile (periodic)
        profile_ctx = get_user_profile_context(ai_path, minutes_since)
        if profile_ctx:
            injections.append(f"<system-reminder>\n{profile_ctx}\n</system-reminder>")

        if lightweight_injection:
            injections.append(lightweight_injection)

        if injections:
            # Log the injection
            total_chars = sum(len(i) for i in injections)
            log(f"Injected: {total_chars} chars (layers: session={bool(session_ctx)}, pins={bool(pins_ctx)}, memory={len(memory_context)}) for: {message[:50]}...")

            # Inject at the beginning (invisible to user)
            injection = "\n".join(injections)
            augmented_message = f"{injection}\n\n{message}"
            print(augmented_message)  # Raw text output
        else:
            # No injection needed
            print(message)  # Raw text output

        # Record this interaction for heartbeat (v4.1/v4.2 with session_id)
        record_heartbeat_interaction(ai_path, session_id=session_id)

    except Exception as e:
        # Log error but don't crash - pass through original
        log(f"[ERROR] {e}")
        # Note: can't re-read stdin, use message if available
        try:
            if message and message.strip():
                print(message)  # Raw text output
            else:
                print("Empty prompt blocked - please type a message.", file=sys.stderr)
                sys.exit(2)
        except NameError:
            print("Empty prompt blocked - please type a message.", file=sys.stderr)
            sys.exit(2)  # Block instead of silent exit to avoid API 400

    finally:
        clear_hook_guard()


if __name__ == '__main__':
    main()
