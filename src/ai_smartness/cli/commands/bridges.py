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
    """Get thread title by full ID match."""
    threads_path = ai_path / "db" / "threads"
    if not threads_path.exists():
        return thread_id[:20] + ".."

    # Try direct file lookup first (faster)
    thread_file = threads_path / f"{thread_id}.json"
    if thread_file.exists():
        try:
            data = json.loads(thread_file.read_text())
            return data.get("title", "")[:25]
        except Exception:
            pass

    # Fallback: search all files
    for thread_file in threads_path.glob("thread_*.json"):
        try:
            data = json.loads(thread_file.read_text())
            if data.get("id") == thread_id:
                return data.get("title", "")[:25]
        except Exception:
            pass

    return thread_id[:20] + ".."


def run_bridges(ai_path: Path, thread_filter: Optional[str], limit: int, show_weight: bool = False) -> int:
    """
    List bridges.

    Args:
        ai_path: Path to .ai directory
        thread_filter: Optional thread ID to filter by
        limit: Maximum number to show
        show_weight: Show weight column

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
    if show_weight:
        print(f"{'Source':<25} | {'Type':<12} | {'Target':<25} | {'Conf':<5} | {'Weight':<6}")
        print("-" * 25 + "-+-" + "-" * 12 + "-+-" + "-" * 25 + "-+-" + "-" * 5 + "-+-" + "-" * 6)
    else:
        print(f"{'Source':<25} | {'Type':<12} | {'Target':<25} | {'Conf':<5}")
        print("-" * 25 + "-+-" + "-" * 12 + "-+-" + "-" * 25 + "-+-" + "-" * 5)

    # Print bridges
    for bridge in bridges[:limit]:
        source_id = bridge.get("source_id", "")
        target_id = bridge.get("target_id", "")
        relation = bridge.get("relation_type", "unknown")
        confidence = bridge.get("confidence", 0)
        weight = bridge.get("weight", 0.5)  # Default for old bridges

        # Get titles for readability
        source_title = get_thread_title(ai_path, source_id)[:23]
        target_title = get_thread_title(ai_path, target_id)[:23]

        if show_weight:
            # Color indicator for weight
            if weight >= 0.7:
                weight_indicator = f"{weight:>5.2f}+"
            elif weight >= 0.3:
                weight_indicator = f"{weight:>5.2f} "
            else:
                weight_indicator = f"{weight:>5.2f}!"
            print(f"{source_title:<25} | {relation:<12} | {target_title:<25} | {confidence:>4.2f} | {weight_indicator}")
        else:
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

    # Show weight stats if requested
    if show_weight:
        weights = [b.get("weight", 0.5) for b in bridges]
        alive = [w for w in weights if w >= 0.05]
        print()
        print("Weight stats:")
        print(f"  Min: {min(weights):.2f}, Max: {max(weights):.2f}, Avg: {sum(weights)/len(weights):.2f}")
        print(f"  Alive: {len(alive)}/{len(bridges)} ({len(alive)/len(bridges)*100:.0f}%)")

    print()
    return 0


def run_prune(ai_path: Path) -> int:
    """
    Apply decay and prune dead bridges.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Exit code
    """
    import sys
    sys.path.insert(0, str(ai_path.parent.parent / "src"))

    try:
        from ai_smartness.storage.bridges import BridgeStorage

        bridges_path = ai_path / "db" / "bridges"
        if not bridges_path.exists():
            print("No bridges directory found.")
            return 0

        storage = BridgeStorage(bridges_path)

        # Get stats before
        all_bridges = storage.get_all()
        total_before = len(all_bridges)

        if total_before == 0:
            print("No bridges to prune.")
            return 0

        print(f"Pruning {total_before} bridges...")
        print()

        # Apply decay and prune
        pruned = storage.prune_dead_bridges()

        # Get stats after
        stats = storage.get_weight_stats()

        print(f"Pruned: {pruned} bridges")
        print(f"Remaining: {stats['alive_count']} alive, {stats['dead_count']} weak")
        print(f"Weight range: {stats['min']:.2f} - {stats['max']:.2f} (avg: {stats['avg']:.2f})")
        print()

        return 0

    except Exception as e:
        print(f"Error during pruning: {e}")
        return 1
