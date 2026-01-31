"""Mode command - View and change operating mode."""

import json
import sys
from pathlib import Path
from typing import Optional


# Mode quotas (duplicated from Thread model for CLI independence)
MODE_QUOTAS = {
    "light": 15,
    "normal": 50,
    "heavy": 100,
    "max": 200
}


def run_mode_status(ai_path: Path) -> int:
    """
    Show current mode status.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Exit code
    """
    # Load config
    config_path = ai_path / "config.json"
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            pass

    mode = config.get("mode", "normal")
    quota = MODE_QUOTAS.get(mode, 50)

    # Count threads
    threads_path = ai_path / "db" / "threads"
    active_count = 0
    suspended_count = 0

    if threads_path.exists():
        active_index = threads_path / "_active.json"
        suspended_index = threads_path / "_suspended.json"

        if active_index.exists():
            try:
                data = json.loads(active_index.read_text())
                active_count = len(data.get("threads", []))
            except Exception:
                pass

        if suspended_index.exists():
            try:
                data = json.loads(suspended_index.read_text())
                suspended_count = len(data.get("threads", []))
            except Exception:
                pass

    available = max(0, quota - active_count)

    print()
    print(f"Current mode: {mode.upper()}")
    print(f"Thread quota: {quota}")
    print()
    print(f"  Active:    {active_count}/{quota}")
    print(f"  Suspended: {suspended_count}")
    print(f"  Available: {available}")
    print()
    print("Available modes:")
    for m, q in MODE_QUOTAS.items():
        marker = " *" if m == mode else ""
        print(f"  {m:<8} {q:>3} threads{marker}")
    print()

    return 0


def run_mode_set(ai_path: Path, new_mode: str) -> int:
    """
    Set operating mode.

    Args:
        ai_path: Path to .ai directory
        new_mode: New mode to set

    Returns:
        Exit code
    """
    if new_mode not in MODE_QUOTAS:
        print(f"Error: Invalid mode '{new_mode}'")
        print(f"Valid modes: {', '.join(MODE_QUOTAS.keys())}")
        return 1

    # Load current config
    config_path = ai_path / "config.json"
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            pass

    old_mode = config.get("mode", "normal")
    old_quota = MODE_QUOTAS.get(old_mode, 50)
    new_quota = MODE_QUOTAS[new_mode]

    if old_mode == new_mode:
        print(f"Already in {new_mode} mode.")
        return 0

    # Update config
    config["mode"] = new_mode
    config["settings"] = config.get("settings", {})
    config["settings"]["active_threads_limit"] = new_quota

    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))

    print()
    print(f"Mode changed: {old_mode} -> {new_mode}")
    print(f"Quota changed: {old_quota} -> {new_quota}")

    # If quota decreased, need to suspend threads
    if new_quota < old_quota:
        suspended = _enforce_quota(ai_path, new_quota)
        if suspended > 0:
            print(f"Suspended {suspended} thread(s) to meet new quota.")

    print()
    return 0


def _enforce_quota(ai_path: Path, quota: int) -> int:
    """
    Enforce thread quota by suspending excess threads.

    Args:
        ai_path: Path to .ai directory
        quota: Maximum active threads

    Returns:
        Number of threads suspended
    """
    sys.path.insert(0, str(ai_path.parent.parent / "src"))

    try:
        from ai_smartness.storage.threads import ThreadStorage

        threads_path = ai_path / "db" / "threads"
        if not threads_path.exists():
            return 0

        storage = ThreadStorage(threads_path)
        return storage.enforce_quota(quota)

    except Exception as e:
        print(f"Warning: Could not enforce quota: {e}")
        return 0
