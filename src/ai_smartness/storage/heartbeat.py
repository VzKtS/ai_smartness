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
from datetime import datetime
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
        "last_interaction_beat": 0
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


def record_interaction(ai_path: Path) -> None:
    """
    Record that an agent interaction occurred at current beat.

    Call this when the agent receives a user message.

    Args:
        ai_path: Path to .ai directory
    """
    heartbeat = load_heartbeat(ai_path)
    heartbeat["last_interaction_at"] = datetime.now().isoformat()
    heartbeat["last_interaction_beat"] = heartbeat["beat"]
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
