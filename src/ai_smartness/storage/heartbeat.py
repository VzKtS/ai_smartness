"""
Heartbeat storage and management.

The heartbeat system provides temporal awareness for the AI agent
using an abstract "beat" counter instead of human time.

Each beat is incremented by the daemon every HEARTBEAT_INTERVAL seconds
(default 5 minutes). The agent perceives time through beats rather than
clock time, which aligns with its intermittent existence.

Storage file: .ai/heartbeat.json
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

HEARTBEAT_FILE = "heartbeat.json"


def load_heartbeat(ai_path: Path) -> dict:
    """
    Load heartbeat state from file.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Heartbeat state dictionary
    """
    filepath = ai_path / HEARTBEAT_FILE
    if not filepath.exists():
        return init_heartbeat(ai_path)

    try:
        with open(filepath, encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # Corrupted file, reinitialize
        return init_heartbeat(ai_path)


def save_heartbeat(ai_path: Path, heartbeat: dict) -> None:
    """
    Save heartbeat state to file.

    Args:
        ai_path: Path to .ai directory
        heartbeat: Heartbeat state dictionary
    """
    filepath = ai_path / HEARTBEAT_FILE
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(heartbeat, f, indent=2)


def init_heartbeat(ai_path: Path) -> dict:
    """
    Initialize heartbeat file with default values.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Initialized heartbeat state
    """
    now = datetime.now().isoformat()
    heartbeat = {
        "beat": 0,
        "started_at": now,
        "last_beat_at": now,
        "last_interaction_at": now,
        "last_interaction_beat": 0,
        "last_session_id": None,
        "last_thread_id": None,
        "last_thread_title": None
    }
    save_heartbeat(ai_path, heartbeat)
    return heartbeat


def increment_beat(ai_path: Path) -> int:
    """
    Increment beat counter. Called by daemon each cycle.

    Args:
        ai_path: Path to .ai directory

    Returns:
        New beat count
    """
    heartbeat = load_heartbeat(ai_path)
    heartbeat["beat"] += 1
    heartbeat["last_beat_at"] = datetime.now().isoformat()
    save_heartbeat(ai_path, heartbeat)
    return heartbeat["beat"]


def record_interaction(
    ai_path: Path,
    session_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    thread_title: Optional[str] = None
) -> None:
    """
    Record that an agent interaction occurred at current beat.

    Call this when the agent receives a user message.

    Args:
        ai_path: Path to .ai directory
        session_id: Current session ID from Claude Code
        thread_id: Current thread ID (hot thread)
        thread_title: Current thread title
    """
    heartbeat = load_heartbeat(ai_path)
    heartbeat["last_interaction_at"] = datetime.now().isoformat()
    heartbeat["last_interaction_beat"] = heartbeat["beat"]

    if session_id:
        heartbeat["last_session_id"] = session_id
    if thread_id:
        heartbeat["last_thread_id"] = thread_id
    if thread_title:
        heartbeat["last_thread_title"] = thread_title

    save_heartbeat(ai_path, heartbeat)


def get_since_last(ai_path: Path) -> int:
    """
    Get number of beats since last interaction.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Number of beats since last interaction
    """
    heartbeat = load_heartbeat(ai_path)
    return heartbeat["beat"] - heartbeat["last_interaction_beat"]


def get_temporal_context(ai_path: Path) -> dict:
    """
    Get heartbeat temporal context for injection.

    Returns beat count and beats since last interaction.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Dictionary with beat and since_last
    """
    heartbeat = load_heartbeat(ai_path)
    return {
        "beat": heartbeat["beat"],
        "since_last": heartbeat["beat"] - heartbeat["last_interaction_beat"]
    }


def is_new_session(session_id: str, ai_path: Path) -> bool:
    """
    Check if this is a new session based on session_id.

    Args:
        session_id: Current session ID from Claude Code
        ai_path: Path to .ai directory

    Returns:
        True if this is a new session, False otherwise
    """
    if not session_id:
        return False
    heartbeat = load_heartbeat(ai_path)
    last_session_id = heartbeat.get("last_session_id")
    return last_session_id is None or session_id != last_session_id


def get_time_since_last(ai_path: Path) -> Optional[timedelta]:
    """
    Get real time since last interaction.

    Args:
        ai_path: Path to .ai directory

    Returns:
        timedelta since last interaction, or None if unknown
    """
    heartbeat = load_heartbeat(ai_path)
    last_at = heartbeat.get("last_interaction_at")
    if not last_at:
        return None
    try:
        return datetime.now() - datetime.fromisoformat(last_at)
    except ValueError:
        return None


# Context window tracking
CONTEXT_WINDOW_SIZE = 200000  # Default context window size
COMPACT_THRESHOLD = 95  # Auto-compact triggers at this %

# Adaptive throttle thresholds
THROTTLE_TIME_SECONDS = 30  # Update interval below 70%
THROTTLE_PERCENT_THRESHOLD = 70  # Above this, switch to delta-based
THROTTLE_PERCENT_DELTA = 5  # Minimum % change to trigger update above 70%


def _should_update_context(heartbeat: dict, new_percent: float) -> bool:
    """
    Check if context should be updated based on adaptive throttle.

    Rules:
    - Below 70%: update every 30 seconds
    - Above 70%: update only if delta >= 5%

    Args:
        heartbeat: Current heartbeat state
        new_percent: New context percentage

    Returns:
        True if should update, False otherwise
    """
    last_updated = heartbeat.get("context_updated_at")
    last_percent = heartbeat.get("context_percent", 0)

    # First update - always allow
    if not last_updated:
        return True

    # Parse last update time
    try:
        last_time = datetime.fromisoformat(last_updated)
        elapsed = (datetime.now() - last_time).total_seconds()
    except (ValueError, TypeError):
        # Can't parse, allow update
        return True

    # Below threshold: time-based throttle (30 seconds)
    if new_percent < THROTTLE_PERCENT_THRESHOLD:
        return elapsed >= THROTTLE_TIME_SECONDS

    # Above threshold: delta-based throttle (5% change)
    delta = abs(new_percent - last_percent)
    return delta >= THROTTLE_PERCENT_DELTA


def update_context_tokens(
    ai_path: Path,
    session_id: str,
    transcript_path: Optional[Path] = None,
    force: bool = False
) -> Optional[dict]:
    """
    Update context token info in heartbeat by reading transcript.

    Uses adaptive throttle:
    - Below 70%: updates every 30 seconds
    - Above 70%: updates only when delta >= 5%

    Args:
        ai_path: Path to .ai directory
        session_id: Current session ID
        transcript_path: Optional path to transcript file
        force: If True, bypass throttle

    Returns:
        Context info dict or None if failed/throttled
    """
    if not transcript_path:
        # Try to find transcript from session_id
        claude_dir = Path.home() / ".claude" / "projects"
        # Find project dir containing this session
        for project_dir in claude_dir.iterdir():
            if not project_dir.is_dir():
                continue
            transcript = project_dir / f"{session_id}.jsonl"
            if transcript.exists():
                transcript_path = transcript
                break

    if not transcript_path or not transcript_path.exists():
        return None

    # Read last usage from transcript
    context_info = _read_last_usage(transcript_path)
    if not context_info:
        return None

    # Load heartbeat to check throttle
    heartbeat = load_heartbeat(ai_path)

    # Check throttle (unless forced)
    if not force and not _should_update_context(heartbeat, context_info["percent"]):
        # Throttled - return cached info without updating
        if "context_percent" in heartbeat:
            return {
                "tokens": heartbeat.get("context_tokens", 0),
                "percent": heartbeat.get("context_percent", 0),
                "cache_tokens": 0,
                "input_tokens": 0,
                "throttled": True
            }
        return None

    # Update heartbeat
    heartbeat["context_tokens"] = context_info["tokens"]
    heartbeat["context_percent"] = context_info["percent"]
    heartbeat["context_window_size"] = CONTEXT_WINDOW_SIZE
    heartbeat["compact_threshold"] = COMPACT_THRESHOLD
    heartbeat["context_updated_at"] = datetime.now().isoformat()
    save_heartbeat(ai_path, heartbeat)

    return context_info


def _read_last_usage(transcript_path: Path) -> Optional[dict]:
    """
    Read the last usage info from a transcript file.

    Args:
        transcript_path: Path to .jsonl transcript

    Returns:
        Dict with tokens and percent, or None
    """
    import re

    try:
        # Read file and find last usage entry
        content = transcript_path.read_text(encoding='utf-8')

        # Find all usage entries with cache_read_input_tokens
        pattern = r'"cache_read_input_tokens":(\d+)'
        matches = re.findall(pattern, content)

        if not matches:
            return None

        # Get the last (most recent) value
        cache_tokens = int(matches[-1])

        # Also get input_tokens from the same context
        input_pattern = r'"input_tokens":(\d+)'
        input_matches = re.findall(input_pattern, content)
        input_tokens = int(input_matches[-1]) if input_matches else 0

        total_tokens = cache_tokens + input_tokens
        percent = round((total_tokens / CONTEXT_WINDOW_SIZE) * 100, 1)

        return {
            "tokens": total_tokens,
            "percent": percent,
            "cache_tokens": cache_tokens,
            "input_tokens": input_tokens
        }
    except Exception:
        return None


def get_context_info(ai_path: Path) -> Optional[dict]:
    """
    Get context info from heartbeat for injection.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Context info dict or None if not available
    """
    heartbeat = load_heartbeat(ai_path)

    if "context_percent" not in heartbeat:
        return None

    return {
        "tokens": heartbeat.get("context_tokens", 0),
        "percent": heartbeat.get("context_percent", 0),
        "window_size": heartbeat.get("context_window_size", CONTEXT_WINDOW_SIZE),
        "compact_threshold": heartbeat.get("compact_threshold", COMPACT_THRESHOLD)
    }
