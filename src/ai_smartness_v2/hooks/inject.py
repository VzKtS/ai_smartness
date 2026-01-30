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
    """Get the ai_smartness_v2 package root."""
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

# Marqueur pour identifier les prompts LLM internes (extractor, synthesis, etc.)
# Format HTML comment - ignoré par le LLM, détectable ici
INTERNAL_PROMPT_MARKER = "<!-- AI_SMARTNESS_INTERNAL_CALL -->"

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

    Filters out:
    - Internal LLM calls (marked prompts from extractor/synthesis)
    - Short messages
    - Acknowledgements

    Args:
        message: User message

    Returns:
        True if prompt should be captured
    """
    # Skip internal LLM calls (marked prompts from extractor, synthesis, etc.)
    if message.startswith(INTERNAL_PROMPT_MARKER):
        return False

    # Legacy: Skip via env var (kept as fallback)
    if os.environ.get('CLAUDE_INTERNAL_CALL') == '1':
        return False

    if len(message) < MIN_PROMPT_LENGTH:
        return False

    message_lower = message.lower().strip()

    # Skip acknowledgements
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

        from ai_smartness_v2.daemon.client import send_capture_with_retry

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

        from ai_smartness_v2.intelligence.memory_retriever import MemoryRetriever

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
# PLAN VALIDATION DETECTION
# =============================================================================

# Patterns indiquant qu'un plan a été approuvé
PLAN_APPROVED_PATTERNS = [
    r"plan\s+approu?v[eé]",
    r"plan\s+approved",
    r"plan\s+valid[eé]",
    r"plan\s+validated",
    r"approu?v[eé]\s+le\s+plan",
    r"approve\s+the\s+plan",
    r"go\s+ahead",
    r"vas-y",
    r"proceed",
    r"lance",
    r"execute",
    r"impl[eé]mente",
    r"^oui$",
    r"^yes$",
    r"^ok$",
    r"^d'accord$",
]


def detect_plan_approval(message: str) -> bool:
    """
    Détecte si le message indique une approbation de plan.

    Args:
        message: User message

    Returns:
        True if plan approval detected
    """
    message_lower = message.lower().strip()

    for pattern in PLAN_APPROVED_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return True

    return False


def find_latest_plan_file() -> Optional[Path]:
    """
    Trouve le fichier plan le plus récent.

    Returns:
        Path to latest plan file, or None
    """
    # Claude Code stocke les plans dans ~/.claude/plans/
    home = Path.home()
    plans_dir = home / ".claude" / "plans"

    if not plans_dir.exists():
        return None

    plan_files = list(plans_dir.glob("*.md"))
    if not plan_files:
        return None

    # Trier par date de modification (plus récent en premier)
    plan_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    return plan_files[0]


def extract_files_from_plan(plan_path: Path) -> list:
    """
    Extrait les chemins de fichiers mentionnés dans un plan.

    Args:
        plan_path: Path to plan file

    Returns:
        List of file paths found in plan
    """
    try:
        content = plan_path.read_text(encoding='utf-8')
    except Exception:
        return []

    files = set()

    # Patterns pour trouver les chemins de fichiers
    patterns = [
        # Fichiers en backticks avec extension
        r'`([^`\s]+\.(?:py|sh|js|ts|tsx|jsx|json|md|yaml|yml|toml|cfg|ini|txt|html|css|sql))`',
        # Dans tableaux markdown
        r'\|\s*`?([^|`\s]+\.(?:py|sh|js|ts|tsx|jsx|json|md|yaml|yml|toml))`?\s*\|',
        # Après "Fichier:" ou "File:"
        r'(?:Fichier|File)[:\s]+`?([^\s`\n]+\.(?:py|sh|js|ts|json|md))`?',
        # Chemins avec src/ ou hooks/
        r'((?:src|hooks|lib|bin)/[^\s`\n\|]+\.(?:py|sh|js|ts|json))',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if match and len(match) > 3:
                # Nettoyer le chemin
                clean_path = match.strip('`"\' ')
                if clean_path:
                    files.add(clean_path)

    return list(files)


def save_plan_state(ai_path: Path, files: list, plan_summary: str = ""):
    """
    Sauvegarde l'état du plan validé.

    Args:
        ai_path: Path to .ai directory
        files: List of validated files
        plan_summary: Optional summary of the plan
    """
    state_file = ai_path / "plan_state.json"

    state = {
        "validated_at": datetime.now().isoformat(),
        "plan_summary": plan_summary,
        "validated_files": files,
        "expires_at": None  # Pas d'expiration par défaut
    }

    try:
        state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        log(f"Plan state saved: {len(files)} files validated")
    except Exception as e:
        log(f"Failed to save plan state: {e}")


def process_plan_approval(message: str, ai_path: Path):
    """
    Traite une approbation de plan détectée.

    Args:
        message: User message
        ai_path: Path to .ai directory
    """
    # Trouver le fichier plan le plus récent
    plan_file = find_latest_plan_file()

    if not plan_file:
        log("Plan approval detected but no plan file found")
        return

    # Extraire les fichiers du plan
    files = extract_files_from_plan(plan_file)

    if not files:
        log(f"Plan approval detected but no files found in {plan_file.name}")
        # Autoriser tout le scope ai_smartness_v2 par défaut
        files = ["src/ai_smartness_v2/*"]

    # Extraire un résumé du plan (première ligne non vide après #)
    plan_summary = ""
    try:
        content = plan_file.read_text(encoding='utf-8')
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('#') and len(line) > 2:
                plan_summary = line.lstrip('#').strip()
                break
    except Exception:
        pass

    # Sauvegarder l'état
    save_plan_state(ai_path, files, plan_summary)

    log(f"Plan validated: {plan_summary[:50]}... ({len(files)} files)")


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

        # Detect and save any user rules in the message
        detected_rule = detect_and_save_user_rule(message, ai_path)
        if detected_rule:
            log(f"Detected user rule: {detected_rule[:50]}...")

        # Detect plan approval and update plan_state.json
        if detect_plan_approval(message):
            process_plan_approval(message, ai_path)
            log(f"Plan approval detected in: {message[:50]}...")

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
