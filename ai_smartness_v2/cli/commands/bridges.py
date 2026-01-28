"""Bridges command - List and filter bridges."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional


def load_bridges(ai_path: Path, thread_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load bridges from database.

    Args:
        ai_path: Path to .ai directory
        thread_filter: Optional thread ID to filter by

    Returns:
        List of bridge data dictionaries
    """
    bridges_path = ai_path / "db" / "bridges"
    bridges = []

    if not bridges_path.exists():
        return bridges

    for bridge_file in bridges_path.glob("bridge_*.json"):
        try:
            data = json.loads(bridge_file.read_text())

            if thread_filter:
                # Filter by thread (source or target)
                if not (
                    data.get("source_id", "").startswith(thread_filter) or
                    data.get("target_id", "").startswith(thread_filter)
                ):
                    continue

            bridges.append(data)
        except Exception:
            pass

    # Sort by confidence (descending)
    bridges.sort(key=lambda b: b.get("confidence", 0), reverse=True)

    return bridges


def get_thread_title(ai_path: Path, thread_id: str) -> str:
    """Get thread title by ID prefix."""
    threads_path = ai_path / "db" / "threads"
    if not threads_path.exists():
        return thread_id[:12] + ".."

    for thread_file in threads_path.glob("thread_*.json"):
        try:
            data = json.loads(thread_file.read_text())
            if data.get("id", "").startswith(thread_id[:12]):
                return data.get("title", "")[:25]
        except Exception:
            pass

    return thread_id[:12] + ".."


def run_bridges(ai_path: Path, thread_filter: Optional[str], limit: int) -> int:
    """
    List bridges.

    Args:
        ai_path: Path to .ai directory
        thread_filter: Optional thread ID to filter by
        limit: Maximum number to show

    Returns:
        Exit code
    """
    bridges = load_bridges(ai_path, thread_filter)

    if not bridges:
        if thread_filter:
            print(f"No bridges found for thread: {thread_filter}")
        else:
            print("No bridges found.")
        return 0

    # Print header
    print()
    print(f"{'Source':<25} | {'Type':<12} | {'Target':<25} | {'Conf':<5}")
    print("-" * 25 + "-+-" + "-" * 12 + "-+-" + "-" * 25 + "-+-" + "-" * 5)

    # Print bridges
    for bridge in bridges[:limit]:
        source_id = bridge.get("source_id", "")
        target_id = bridge.get("target_id", "")
        relation = bridge.get("relation_type", "unknown")
        confidence = bridge.get("confidence", 0)

        # Get titles for readability
        source_title = get_thread_title(ai_path, source_id)[:23]
        target_title = get_thread_title(ai_path, target_id)[:23]

        print(f"{source_title:<25} | {relation:<12} | {target_title:<25} | {confidence:>4.2f}")

    total = len(bridges)
    if total > limit:
        print(f"\n... and {total - limit} more. Use --limit to show more.")

    # Show summary by type
    print()
    print("Bridge types:")
    type_counts = {}
    for b in bridges:
        rel = b.get("relation_type", "unknown")
        type_counts[rel] = type_counts.get(rel, 0) + 1
    for rel, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {rel}: {count}")

    print()
    return 0
