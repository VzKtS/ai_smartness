"""Status command - Show memory overview."""

import json
from pathlib import Path
from datetime import datetime


def run_status(ai_path: Path) -> int:
    """
    Show memory status overview.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Exit code
    """
    db_path = ai_path / "db"
    threads_path = db_path / "threads"
    bridges_path = db_path / "bridges"
    config_path = ai_path / "config.json"

    # Count threads by status
    active_count = 0
    suspended_count = 0
    archived_count = 0
    last_active = None
    current_thread = None

    if threads_path.exists():
        for thread_file in threads_path.glob("thread_*.json"):
            try:
                data = json.loads(thread_file.read_text())
                status = data.get("status", "active")
                if status == "active":
                    active_count += 1
                elif status == "suspended":
                    suspended_count += 1
                else:
                    archived_count += 1

                # Track most recent
                thread_last = data.get("last_active")
                if thread_last:
                    if last_active is None or thread_last > last_active:
                        last_active = thread_last
                        current_thread = data.get("title", "")[:40]
            except Exception:
                pass

    # Count bridges
    bridge_count = 0
    if bridges_path.exists():
        bridge_count = len(list(bridges_path.glob("bridge_*.json")))

    # Load config
    project_name = "Unknown"
    thread_mode = "normal"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            project_name = config.get("project_name", "Unknown")
            thread_mode = config.get("settings", {}).get("thread_mode", "normal")
        except Exception:
            pass

    # Format last active
    last_active_str = "Never"
    if last_active:
        try:
            dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
            last_active_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            last_active_str = last_active[:16]

    # Print status
    width = 48
    print()
    print("+" + "-" * (width - 2) + "+")
    print(f"| {'AI Smartness v2 - Memory Status':^{width-4}} |")
    print("+" + "-" * (width - 2) + "+")
    print(f"| Project: {project_name:<{width-13}} |")
    print(f"| Mode:    {thread_mode:<{width-13}} |")
    print("+" + "-" * (width - 2) + "+")
    print(f"| Threads: {active_count} active, {suspended_count} suspended{' ' * (width - 35 - len(str(active_count)) - len(str(suspended_count)))} |")
    print(f"| Bridges: {bridge_count} connections{' ' * (width - 25 - len(str(bridge_count)))} |")
    print(f"| Last:    {last_active_str:<{width-13}} |")
    if current_thread:
        print(f"| Current: \"{current_thread}\"{' ' * max(0, width - 15 - len(current_thread))} |")
    print("+" + "-" * (width - 2) + "+")
    print()

    return 0
