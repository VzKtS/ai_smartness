"""
Session and User Profile management for AI Smartness V5.1.

Handles:
- Session state tracking (work continuity between sessions)
- User profile (persistent personalization)
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SessionState:
    """
    Tracks current work session state for continuity.

    Stored in: .ai/session_state.json
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "active"  # active, idle, ended

    # Current work context
    current_work: Dict[str, Any] = field(default_factory=lambda: {
        "thread_id": None,
        "thread_title": None,
        "last_user_message": None,
        "last_agent_action": None,
        "intent": None
    })

    # Files modified in this session
    files_modified: List[Dict[str, str]] = field(default_factory=list)

    # Pending tasks (from TodoWrite if available)
    pending_tasks: List[str] = field(default_factory=list)

    # Tool history (last N tool calls)
    tool_history: List[Dict[str, str]] = field(default_factory=list)

    def update_activity(self):
        """Mark session as active with current timestamp."""
        self.last_activity_at = datetime.now().isoformat()
        self.status = "active"

    def add_file_modified(self, path: str, action: str, summary: str = ""):
        """Track a file modification."""
        self.files_modified.append({
            "path": path,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "summary": summary[:100] if summary else ""
        })
        # Keep last 20 files
        self.files_modified = self.files_modified[-20:]
        self.update_activity()

    def add_tool_call(self, tool: str, target: str):
        """Track a tool call."""
        self.tool_history.append({
            "tool": tool,
            "target": target,
            "at": datetime.now().strftime("%H:%M:%S")
        })
        # Keep last 50 tool calls
        self.tool_history = self.tool_history[-50:]
        self.update_activity()

    def set_current_thread(self, thread_id: str, thread_title: str):
        """Set the current working thread."""
        self.current_work["thread_id"] = thread_id
        self.current_work["thread_title"] = thread_title
        self.update_activity()

    def set_user_message(self, message: str):
        """Track last user message."""
        self.current_work["last_user_message"] = message[:200]
        self.update_activity()

    def set_agent_action(self, action: str):
        """Track last agent action."""
        self.current_work["last_agent_action"] = action[:100]
        self.update_activity()

    def set_intent(self, intent: str):
        """Set current work intent."""
        self.current_work["intent"] = intent[:200]
        self.update_activity()

    def set_pending_tasks(self, tasks: List[str]):
        """Update pending tasks list."""
        self.pending_tasks = tasks[:10]  # Keep max 10
        self.update_activity()

    def mark_idle(self):
        """Mark session as idle."""
        self.status = "idle"

    def mark_ended(self):
        """Mark session as ended."""
        self.status = "ended"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
            "status": self.status,
            "current_work": self.current_work,
            "files_modified": self.files_modified,
            "pending_tasks": self.pending_tasks,
            "tool_history": self.tool_history
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        """Deserialize from dictionary."""
        session = cls()
        session.session_id = data.get("session_id", session.session_id)
        session.started_at = data.get("started_at", session.started_at)
        session.last_activity_at = data.get("last_activity_at", session.last_activity_at)
        session.status = data.get("status", "active")
        session.current_work = data.get("current_work", session.current_work)
        session.files_modified = data.get("files_modified", [])
        session.pending_tasks = data.get("pending_tasks", [])
        session.tool_history = data.get("tool_history", [])
        return session

    def get_minutes_since_activity(self) -> float:
        """Calculate minutes since last activity."""
        try:
            last = datetime.fromisoformat(self.last_activity_at)
            return (datetime.now() - last).total_seconds() / 60
        except Exception:
            return 999.0


@dataclass
class UserProfile:
    """
    Persistent user profile for personalization.

    Stored in: .ai/user_profile.json
    """
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Identity
    identity: Dict[str, Any] = field(default_factory=lambda: {
        "role": "user",  # user, developer, owner
        "relationship": "user",  # user, contributor, owner
        "name": None
    })

    # Preferences
    preferences: Dict[str, Any] = field(default_factory=lambda: {
        "language": "en",
        "verbosity": "normal",  # concise, normal, detailed
        "emoji_usage": False,
        "technical_level": "intermediate"  # beginner, intermediate, expert
    })

    # Behavioral patterns (learned)
    patterns: Dict[str, Any] = field(default_factory=lambda: {
        "active_hours": [],
        "session_avg_duration_min": 0,
        "common_tasks": []
    })

    # Custom rules
    context_rules: List[str] = field(default_factory=list)

    def update(self):
        """Mark profile as updated."""
        self.updated_at = datetime.now().isoformat()

    def set_role(self, role: str):
        """Set user role."""
        if role in ["user", "developer", "owner"]:
            self.identity["role"] = role
            self.update()

    def set_relationship(self, relationship: str):
        """Set relationship to project."""
        if relationship in ["user", "contributor", "owner"]:
            self.identity["relationship"] = relationship
            self.update()

    def set_preference(self, key: str, value: Any):
        """Set a preference."""
        if key in self.preferences:
            self.preferences[key] = value
            self.update()

    def add_rule(self, rule: str):
        """Add a context rule."""
        if rule not in self.context_rules:
            self.context_rules.append(rule)
            self.update()

    def remove_rule(self, rule: str):
        """Remove a context rule."""
        if rule in self.context_rules:
            self.context_rules.remove(rule)
            self.update()

    def update_active_hour(self, hour: int):
        """Update active hours pattern."""
        hour_range = f"{hour:02d}:00-{(hour+1)%24:02d}:00"
        if hour_range not in self.patterns["active_hours"]:
            self.patterns["active_hours"].append(hour_range)
            # Keep only 5 most common ranges
            self.patterns["active_hours"] = self.patterns["active_hours"][-5:]
            self.update()

    def update_common_task(self, task: str):
        """Update common tasks pattern."""
        if task not in self.patterns["common_tasks"]:
            self.patterns["common_tasks"].append(task)
            self.patterns["common_tasks"] = self.patterns["common_tasks"][-5:]
            self.update()

    def detect_from_message(self, message: str):
        """Detect profile info from user message."""
        msg_lower = message.lower()

        # Detect ownership
        if any(p in msg_lower for p in ["mon projet", "my project", "j'ai créé", "i created"]):
            self.set_relationship("owner")

        # Detect developer role
        if any(p in msg_lower for p in ["implement", "debug", "refactor", "implémente"]):
            self.set_role("developer")

        # Detect technical level
        technical_terms = ["api", "async", "hook", "mcp", "daemon", "socket", "embedding"]
        if sum(1 for t in technical_terms if t in msg_lower) >= 3:
            self.set_preference("technical_level", "expert")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "identity": self.identity,
            "preferences": self.preferences,
            "patterns": self.patterns,
            "context_rules": self.context_rules
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Deserialize from dictionary."""
        profile = cls()
        profile.created_at = data.get("created_at", profile.created_at)
        profile.updated_at = data.get("updated_at", profile.updated_at)
        profile.identity = {**profile.identity, **data.get("identity", {})}
        profile.preferences = {**profile.preferences, **data.get("preferences", {})}
        profile.patterns = {**profile.patterns, **data.get("patterns", {})}
        profile.context_rules = data.get("context_rules", [])
        return profile


# === File I/O Functions ===

def load_session_state(ai_path: Path) -> SessionState:
    """Load session state from file or create new."""
    state_file = ai_path / "session_state.json"
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            return SessionState.from_dict(data)
        except Exception:
            pass
    return SessionState()


def save_session_state(ai_path: Path, state: SessionState):
    """Save session state to file."""
    state_file = ai_path / "session_state.json"
    try:
        state_file.write_text(
            json.dumps(state.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception:
        pass


def load_user_profile(ai_path: Path) -> UserProfile:
    """Load user profile from file or create new."""
    profile_file = ai_path / "user_profile.json"
    if profile_file.exists():
        try:
            data = json.loads(profile_file.read_text(encoding="utf-8"))
            return UserProfile.from_dict(data)
        except Exception:
            pass
    return UserProfile()


def save_user_profile(ai_path: Path, profile: UserProfile):
    """Save user profile to file."""
    profile_file = ai_path / "user_profile.json"
    try:
        profile_file.write_text(
            json.dumps(profile.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception:
        pass


def load_pins(ai_path: Path) -> List[dict]:
    """Load pinned content from file."""
    pins_file = ai_path / "pins.json"
    if pins_file.exists():
        try:
            data = json.loads(pins_file.read_text(encoding="utf-8"))
            pins = data.get("pins", [])
            # Filter out expired pins
            now = datetime.now()
            active_pins = []
            for pin in pins:
                expires = pin.get("expires_at")
                if expires:
                    try:
                        if datetime.fromisoformat(expires) < now:
                            continue
                    except Exception:
                        pass
                active_pins.append(pin)
            return active_pins
        except Exception:
            pass
    return []
