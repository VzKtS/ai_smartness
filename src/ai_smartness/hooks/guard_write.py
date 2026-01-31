#!/usr/bin/env python3
"""
Guard Write Hook - Bloque les modifications sans plan validé.

Hook PreToolUse pour Edit/Write.
Exit 0 = autorisé
Exit 2 = bloqué

Usage: Configuré dans .claude/settings.json comme hook PreToolUse
       Reçoit JSON via stdin de Claude Code
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

HOOK_GUARD_ENV = "AI_SMARTNESS_HOOK_RUNNING"


def check_hook_guard() -> bool:
    """Check if we're already inside a hook."""
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
    """Find the project root (directory containing .ai)."""
    current = get_package_root().parent

    for parent in [current] + list(current.parents):
        if (parent / ".ai").exists():
            return parent
        if len(parent.parts) <= 1:
            break

    return None


def get_ai_path() -> Path:
    """Get the .ai directory path."""
    # First try: package-local .ai
    package_dir = get_package_root()
    ai_path = package_dir / ".ai"
    if ai_path.exists():
        return ai_path

    # Second try: project root .ai
    project_root = get_project_root()
    if project_root:
        return project_root / ".ai"

    # Fallback: create in package
    ai_path.mkdir(parents=True, exist_ok=True)
    return ai_path


# =============================================================================
# LOGGING
# =============================================================================

def get_log_path() -> Path:
    """Get the log file path."""
    ai_path = get_ai_path()
    return ai_path / "guard_write.log"


def log(message: str):
    """Write to guard_write log."""
    try:
        log_path = get_log_path()
        with open(log_path, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


# =============================================================================
# PLAN STATE MANAGEMENT
# =============================================================================

def load_plan_state(ai_path: Path) -> dict:
    """
    Charge l'état des plans validés.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Plan state dictionary
    """
    state_file = ai_path / "plan_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, IOError):
            pass

    return {
        "validated_files": [],
        "validated_at": None,
        "plan_summary": None,
        "expires_at": None
    }


def is_file_in_plan(file_path: str, state: dict) -> bool:
    """
    Vérifie si le fichier est dans un plan validé.

    Args:
        file_path: Path to check
        state: Plan state dictionary

    Returns:
        True if file is allowed, False otherwise
    """
    if not file_path:
        return False

    validated_files = state.get("validated_files", [])
    if not validated_files:
        return False

    # Normaliser le chemin
    try:
        file_path_resolved = str(Path(file_path).resolve())
    except Exception:
        file_path_resolved = file_path

    for allowed in validated_files:
        try:
            # Pattern avec wildcard (ex: "src/ai_smartness/*")
            if allowed.endswith("/*"):
                prefix = allowed[:-2]
                prefix_resolved = str(Path(prefix).resolve())
                if file_path_resolved.startswith(prefix_resolved):
                    return True
            else:
                # Chemin exact
                allowed_resolved = str(Path(allowed).resolve())
                if file_path_resolved == allowed_resolved:
                    return True
        except Exception:
            # En cas d'erreur, comparer les chaînes directement
            if file_path in allowed or allowed in file_path:
                return True

    return False


def check_expiration(state: dict) -> bool:
    """
    Vérifie si le plan a expiré.

    Args:
        state: Plan state dictionary

    Returns:
        True if still valid, False if expired
    """
    expires_at = state.get("expires_at")
    if not expires_at:
        return True  # Pas d'expiration = toujours valide

    try:
        expiry = datetime.fromisoformat(expires_at)
        return datetime.now() < expiry
    except (ValueError, TypeError):
        return True


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


def get_tool_data_from_stdin() -> dict:
    """
    Get tool data from stdin (Claude Code sends JSON).

    Returns:
        Tool data dictionary
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
# MAIN
# =============================================================================

def main():
    """Main entry point for guard_write hook."""

    # ANTI-AUTOHOOK GUARD
    if not check_hook_guard():
        sys.exit(0)

    set_hook_guard()

    try:
        # Lire input de Claude Code
        data = get_tool_data_from_stdin()

        if not data:
            log("[PASS] No input data")
            sys.exit(0)

        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})

        # Seulement pour Edit et Write
        if tool_name not in ["Edit", "Write"]:
            log(f"[PASS] Tool '{tool_name}' not Edit/Write")
            sys.exit(0)

        # Extraire le chemin du fichier
        file_path = ""
        if isinstance(tool_input, dict):
            file_path = tool_input.get("file_path", "")

        if not file_path:
            log(f"[PASS] No file_path in {tool_name}")
            sys.exit(0)

        # Charger état du plan
        ai_path = get_ai_path()
        state = load_plan_state(ai_path)

        # Vérifier expiration
        if not check_expiration(state):
            log(f"[BLOCKED] Plan expired - {file_path}")
            print("BLOQUÉ: Le plan a expiré.", file=sys.stderr)
            print("Validez un nouveau plan avant de modifier le code.", file=sys.stderr)
            sys.exit(2)

        # Vérifier si fichier autorisé
        if is_file_in_plan(file_path, state):
            log(f"[ALLOWED] {file_path}")
            sys.exit(0)
        else:
            # BLOQUER
            file_name = Path(file_path).name
            log(f"[BLOCKED] {file_path} - No validated plan")

            print(f"BLOQUÉ: Modification de '{file_name}' non autorisée.", file=sys.stderr)
            print("", file=sys.stderr)
            print("Un mode plan doit être validé avant toute modification de code.", file=sys.stderr)
            print("Utilisez EnterPlanMode pour créer un plan, puis obtenez l'approbation.", file=sys.stderr)
            sys.exit(2)

    except Exception as e:
        log(f"[ERROR] {e}")
        # En cas d'erreur, laisser passer (fail-open pour éviter de bloquer en cas de bug)
        sys.exit(0)

    finally:
        clear_hook_guard()


if __name__ == '__main__':
    main()
