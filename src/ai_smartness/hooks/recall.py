"""
Recall handler for AI Smartness v4.0.

Handles active memory recall queries triggered by Read(".ai/recall/<query>").
Searches threads and bridges, formats results for agent consumption.

Features:
- Search by query or thread ID
- Include suspended threads (with score threshold)
- Auto-reactivate suspended threads with high relevance
- Format with Last active timestamp for staleness evaluation
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Import path setup
def _setup_imports():
    """Setup import paths for package modules."""
    package_dir = Path(__file__).parent.parent
    package_parent = package_dir.parent
    if str(package_parent) not in sys.path:
        sys.path.insert(0, str(package_parent))

_setup_imports()


def handle_recall(query: str, ai_path: Path) -> str:
    """
    Handle a recall query and return formatted memory context.

    Args:
        query: Search query or thread ID
        ai_path: Path to .ai directory

    Returns:
        Formatted memory context string
    """
    try:
        from ai_smartness.intelligence.memory_retriever import MemoryRetriever

        db_path = ai_path / "db"
        retriever = MemoryRetriever(db_path)

        # Search with suspended threads included (limit 5 for compact output)
        threads, bridges = retriever.search(query, include_suspended=True, limit=5)

        # Format results
        return format_recall_result(query, threads, bridges)

    except ImportError as e:
        return f"# Memory Recall Error\n\nFailed to import MemoryRetriever: {e}"
    except Exception as e:
        return f"# Memory Recall Error\n\nError during recall: {e}"


def format_recall_result(
    query: str,
    threads: List[Dict],
    bridges: List[Dict]
) -> str:
    """
    Format recall results as readable memory context.

    Args:
        query: Original query
        threads: List of matching threads
        bridges: List of related bridges

    Returns:
        Formatted string for agent consumption
    """
    lines = [
        f"# Memory Recall: {query}",
        f"Query executed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]

    # Threads section
    if threads:
        lines.append(f"## Matching Threads ({len(threads)} found)")
        lines.append("")

        for thread in threads:
            status = thread.get("status", "active").upper()
            title = thread.get("title", "Untitled")[:60]
            weight = thread.get("weight", 0.5)
            topics = thread.get("topics", [])[:5]
            summary = thread.get("summary", "")[:100]
            last_active = thread.get("last_active", "")
            similarity = thread.get("_similarity", 0)  # Added by search()
            reactivated = thread.get("_reactivated", False)

            # Calculate "last active" human-readable
            last_active_str = _format_last_active(last_active)

            lines.append(f"### [{status}] {title}")
            lines.append(f"Weight: {weight:.2f} | Topics: {', '.join(topics)}")

            if summary:
                lines.append(f"Summary: {summary}")

            lines.append(f"Last active: {last_active_str}")

            if similarity > 0:
                lines.append(f"Match score: {similarity:.2f}")

            if reactivated:
                lines.append("-> Reactivated by this recall")

            lines.append("")

    else:
        lines.append("## No matching threads found")
        lines.append("")

    # Bridges section (limit to 5)
    if bridges:
        bridges_shown = bridges[:5]
        lines.append(f"## Related Bridges ({len(bridges_shown)} of {len(bridges)})")
        lines.append("")

        for bridge in bridges_shown:
            source_title = bridge.get("_source_title", bridge.get("source_id", "")[:8])
            target_title = bridge.get("_target_title", bridge.get("target_id", "")[:8])
            bridge_type = bridge.get("bridge_type", "RELATES")
            weight = bridge.get("weight", 0.5)

            lines.append(f"- {source_title} -> {target_title} ({bridge_type}, weight: {weight:.2f})")

        lines.append("")

    return "\n".join(lines)


def _format_last_active(iso_timestamp: str) -> str:
    """
    Format ISO timestamp as human-readable "X days ago".

    Args:
        iso_timestamp: ISO format timestamp string

    Returns:
        Human-readable string like "2 days ago"
    """
    if not iso_timestamp:
        return "unknown"

    try:
        last_active = datetime.fromisoformat(iso_timestamp)
        now = datetime.now()
        delta = now - last_active

        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                minutes = delta.seconds // 60
                return f"{minutes} minutes ago" if minutes > 1 else "just now"
            return f"{hours} hours ago" if hours > 1 else "1 hour ago"
        elif delta.days == 1:
            return "1 day ago"
        else:
            return f"{delta.days} days ago"

    except (ValueError, TypeError):
        return "unknown"
