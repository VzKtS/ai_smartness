"""Threads commands - List and show thread details."""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def load_threads(ai_path: Path, status_filter: str = "all") -> List[Dict[str, Any]]:
    """
    Load threads from database.

    Args:
        ai_path: Path to .ai directory
        status_filter: Status to filter by (active, suspended, archived, all)

    Returns:
        List of thread data dictionaries
    """
    threads_path = ai_path / "db" / "threads"
    threads = []

    if not threads_path.exists():
        return threads

    for thread_file in threads_path.glob("thread_*.json"):
        try:
            data = json.loads(thread_file.read_text())
            status = data.get("status", "active")

            if status_filter != "all" and status != status_filter:
                continue

            threads.append(data)
        except Exception:
            pass

    # Sort by weight (descending), then by last_active
    threads.sort(key=lambda t: (t.get("weight", 0), t.get("last_active", "")), reverse=True)

    return threads


def run_threads(ai_path: Path, status_filter: str, limit: int, show_weight: bool = False) -> int:
    """
    List threads.

    Args:
        ai_path: Path to .ai directory
        status_filter: Status to filter by
        limit: Maximum number to show
        show_weight: Show detailed weight info

    Returns:
        Exit code
    """
    threads = load_threads(ai_path, status_filter)

    if not threads:
        print(f"No {status_filter} threads found.")
        return 0

    # Print header
    print()
    print(f"{'ID':<12} | {'Title':<35} | {'Status':<10} | {'Weight':<6} | {'Msgs':<4}")
    print("-" * 12 + "-+-" + "-" * 35 + "-+-" + "-" * 10 + "-+-" + "-" * 6 + "-+-" + "-" * 4)

    # Print threads
    for thread in threads[:limit]:
        thread_id = thread.get("id", "")[:10] + ".."
        title = thread.get("title", "")[:33]
        if len(thread.get("title", "")) > 33:
            title += ".."
        status = thread.get("status", "active")
        weight = thread.get("weight", 0)
        msgs = len(thread.get("messages", []))

        # Weight indicator for --show-weight
        if show_weight:
            if weight >= 0.5:
                weight_str = f"{weight:>5.2f}+"
            elif weight >= 0.1:
                weight_str = f"{weight:>5.2f} "
            else:
                weight_str = f"{weight:>5.2f}!"
        else:
            weight_str = f"{weight:>5.2f} "

        print(f"{thread_id:<12} | {title:<35} | {status:<10} | {weight_str} | {msgs:>4}")

    total = len(threads)
    if total > limit:
        print(f"\n... and {total - limit} more. Use --limit to show more.")

    # Show weight stats if requested
    if show_weight:
        all_threads = load_threads(ai_path, "all")
        if all_threads:
            weights = [t.get("weight", 0) for t in all_threads]
            active = [t for t in all_threads if t.get("status") == "active"]
            suspended = [t for t in all_threads if t.get("status") == "suspended"]
            print()
            print("Weight stats:")
            print(f"  Min: {min(weights):.2f}, Max: {max(weights):.2f}, Avg: {sum(weights)/len(weights):.2f}")
            print(f"  Active: {len(active)}, Suspended: {len(suspended)}")

    print()
    return 0


def run_threads_prune(ai_path: Path) -> int:
    """
    Apply decay and suspend low-weight threads.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Exit code
    """
    import sys
    sys.path.insert(0, str(ai_path.parent.parent / "src"))

    try:
        from ai_smartness_v2.storage.threads import ThreadStorage

        threads_path = ai_path / "db" / "threads"
        if not threads_path.exists():
            print("No threads directory found.")
            return 0

        storage = ThreadStorage(threads_path)

        # Get stats before
        all_threads = storage.get_all()
        active_before = len([t for t in all_threads if t.status.value == "active"])

        if active_before == 0:
            print("No active threads to prune.")
            return 0

        # Load mode quota from config
        config_path = ai_path / "config.json"
        quota = 50  # default
        mode = "normal"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                mode = config.get("mode", "normal")
                quota = config.get("settings", {}).get("active_threads_limit", 50)
            except Exception:
                pass

        print(f"Pruning threads (mode: {mode}, quota: {quota})...")
        print()

        # Apply decay and prune
        suspended = storage.prune_threads(mode_quota=quota)

        # Get stats after
        stats = storage.get_weight_stats()

        print(f"Suspended: {suspended} thread(s)")
        print(f"Remaining: {stats['active_count']} active, {stats['suspended_count']} suspended")
        if stats['total'] > 0:
            print(f"Weight range: {stats['min']:.2f} - {stats['max']:.2f} (avg: {stats['avg']:.2f})")
        print()

        return 0

    except Exception as e:
        print(f"Error during pruning: {e}")
        return 1


def run_thread_detail(ai_path: Path, thread_id: str) -> int:
    """
    Show detailed information about a thread.

    Args:
        ai_path: Path to .ai directory
        thread_id: Thread ID or prefix

    Returns:
        Exit code
    """
    threads_path = ai_path / "db" / "threads"
    bridges_path = ai_path / "db" / "bridges"

    if not threads_path.exists():
        print("No threads found.")
        return 1

    # Find thread by ID prefix
    thread_data = None
    for thread_file in threads_path.glob("thread_*.json"):
        try:
            data = json.loads(thread_file.read_text())
            if data.get("id", "").startswith(thread_id):
                thread_data = data
                break
        except Exception:
            pass

    if not thread_data:
        print(f"Thread not found: {thread_id}")
        return 1

    # Print thread details
    print()
    print("=" * 60)
    print(f"Thread: {thread_data.get('title', 'Untitled')}")
    print("=" * 60)
    print(f"ID:        {thread_data.get('id', '')}")
    print(f"Status:    {thread_data.get('status', 'unknown')}")
    print(f"Weight:    {thread_data.get('weight', 0):.3f}")
    print(f"Origin:    {thread_data.get('origin_type', 'unknown')}")
    print(f"Created:   {thread_data.get('created_at', 'unknown')[:19]}")
    print(f"Last:      {thread_data.get('last_active', 'unknown')[:19]}")

    # Topics
    topics = thread_data.get("topics", [])
    if topics:
        print(f"Topics:    {', '.join(topics[:5])}")

    # Messages summary
    messages = thread_data.get("messages", [])
    print(f"\nMessages ({len(messages)}):")
    for i, msg in enumerate(messages[:5]):
        content = msg.get("content", "")[:60]
        source = msg.get("source_type", "unknown")
        print(f"  {i+1}. [{source}] {content}...")
    if len(messages) > 5:
        print(f"  ... and {len(messages) - 5} more")

    # Find connected bridges
    thread_id_full = thread_data.get("id", "")
    incoming = []
    outgoing = []

    if bridges_path.exists():
        for bridge_file in bridges_path.glob("bridge_*.json"):
            try:
                bridge = json.loads(bridge_file.read_text())
                if bridge.get("source_id") == thread_id_full:
                    outgoing.append(bridge)
                elif bridge.get("target_id") == thread_id_full:
                    incoming.append(bridge)
            except Exception:
                pass

    if incoming or outgoing:
        print(f"\nBridges:")
        if outgoing:
            print(f"  Outgoing ({len(outgoing)}):")
            for b in outgoing[:3]:
                print(f"    -> {b.get('target_id', '')[:12]}.. ({b.get('relation_type', '')})")
        if incoming:
            print(f"  Incoming ({len(incoming)}):")
            for b in incoming[:3]:
                print(f"    <- {b.get('source_id', '')[:12]}.. ({b.get('relation_type', '')})")

    print()
    return 0
