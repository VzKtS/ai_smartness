"""
StorageManager - Central storage coordinator for AI Smartness.

Manages the database structure and provides access to specialized storage classes.

v7: Multi-agent support - when agent_id is provided and project is in multi mode,
storage is partitioned under .ai/db/agents/{agent_id}/.
"""

import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime


def detect_agent_id(root_path: Path) -> Optional[str]:
    """
    Detect the current agent_id from .mcp_smartness_agent file.

    Returns:
        agent_id string if found in multi mode, None for simple mode
    """
    agent_file = Path(root_path) / ".mcp_smartness_agent"
    if not agent_file.exists():
        return None

    try:
        data = json.loads(agent_file.read_text(encoding="utf-8"))
        project_mode = data.get("project_mode", "simple")
        agents = data.get("agents", [])

        if project_mode == "multi" and len(agents) >= 2:
            # In multi mode, we need to know which agent WE are
            # Check AI_SMARTNESS_AGENT_ID env var as override
            import os
            env_id = os.environ.get("AI_SMARTNESS_AGENT_ID")
            if env_id:
                return env_id

            # Fallback: if only one agent declared, use that one
            if len(agents) == 1:
                return agents[0].get("id")

            # Multiple agents but no env var - can't determine which one we are
            # Return None to fall back to simple mode
            return None

        return None
    except (json.JSONDecodeError, IOError):
        return None


def get_project_mode(root_path: Path) -> str:
    """
    Get the project mode from .mcp_smartness_agent file.

    Returns:
        'simple' or 'multi'
    """
    agent_file = Path(root_path) / ".mcp_smartness_agent"
    if not agent_file.exists():
        return "simple"

    try:
        data = json.loads(agent_file.read_text(encoding="utf-8"))
        return data.get("project_mode", "simple")
    except (json.JSONDecodeError, IOError):
        return "simple"


def get_registered_agents(root_path: Path) -> List[dict]:
    """
    Get list of registered agents from .mcp_smartness_agent file.

    Returns:
        List of agent dicts with id, name, role
    """
    agent_file = Path(root_path) / ".mcp_smartness_agent"
    if not agent_file.exists():
        return []

    try:
        data = json.loads(agent_file.read_text(encoding="utf-8"))
        return data.get("agents", [])
    except (json.JSONDecodeError, IOError):
        return []


class StorageManager:
    """
    Central storage coordinator.

    Initializes and manages the database structure.
    Provides access to ThreadStorage and BridgeStorage.

    v7: Supports multi-agent mode where each agent has isolated storage
    under .ai/db/agents/{agent_id}/.
    """

    DB_STRUCTURE = {
        "threads": {},
        "bridges": {},
    }

    MAX_AGENTS_PER_PROJECT = 5

    def __init__(self, root_path: Path, agent_id: Optional[str] = None):
        """
        Initialize storage manager.

        Args:
            root_path: Root path of the project
            agent_id: Optional agent ID for multi-agent mode.
                      If None, auto-detects from .mcp_smartness_agent.
                      If False (explicit), forces simple mode.
        """
        self.root_path = Path(root_path)
        self.ai_path = self.root_path / ".ai"
        self.agent_id = agent_id
        self.project_mode = get_project_mode(self.root_path)

        # Determine db_path based on mode
        if self.agent_id and self.project_mode == "multi":
            # Multi-agent: partitioned storage
            self.db_path = self.ai_path / "db" / "agents" / self.agent_id
        else:
            # Simple mode: legacy path
            self.db_path = self.ai_path / "db"

        # Ensure structure exists
        self._ensure_structure()

        # Lazy-loaded storage instances
        self._thread_storage: Optional["ThreadStorage"] = None
        self._bridge_storage: Optional["BridgeStorage"] = None

    def _ensure_structure(self):
        """Ensure database directory structure exists."""
        for subdir in self.DB_STRUCTURE.keys():
            (self.db_path / subdir).mkdir(parents=True, exist_ok=True)

        # Create meta file if not exists
        meta_path = self.db_path / "_meta.json"
        if not meta_path.exists():
            meta = {
                "version": "7.0.0",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "agent_id": self.agent_id,
                "project_mode": self.project_mode
            }
            self._write_json(meta_path, meta)

    @property
    def threads(self) -> "ThreadStorage":
        """Get ThreadStorage instance (lazy-loaded)."""
        if self._thread_storage is None:
            from .threads import ThreadStorage
            self._thread_storage = ThreadStorage(self.db_path / "threads")
        return self._thread_storage

    @property
    def bridges(self) -> "BridgeStorage":
        """Get BridgeStorage instance (lazy-loaded)."""
        if self._bridge_storage is None:
            from .bridges import BridgeStorage
            self._bridge_storage = BridgeStorage(self.db_path / "bridges")
        return self._bridge_storage

    def _write_json(self, path: Path, data: dict):
        """Write JSON file atomically."""
        temp_path = path.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            temp_path.rename(path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _read_json(self, path: Path) -> Optional[dict]:
        """Read JSON file safely."""
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return None

    def update_meta(self):
        """Update the meta file with current timestamp."""
        meta_path = self.db_path / "_meta.json"
        meta = self._read_json(meta_path) or {}
        meta["last_updated"] = datetime.now().isoformat()
        self._write_json(meta_path, meta)

    def get_stats(self) -> dict:
        """Get database statistics."""
        thread_count = len(list((self.db_path / "threads").glob("thread_*.json")))
        bridge_count = len(list((self.db_path / "bridges").glob("bridge_*.json")))

        stats = {
            "threads": thread_count,
            "bridges": bridge_count,
            "db_path": str(self.db_path),
            "project_mode": self.project_mode,
        }

        if self.agent_id:
            stats["agent_id"] = self.agent_id

        return stats

    @classmethod
    def init_agent(cls, root_path: Path, agent_id: str) -> "StorageManager":
        """
        Initialize storage structure for a new agent in multi-mode.

        Creates .ai/db/agents/{agent_id}/ with threads/ and bridges/ subdirs.

        Args:
            root_path: Project root path
            agent_id: Agent identifier

        Returns:
            StorageManager instance for this agent

        Raises:
            ValueError: If max agents exceeded or invalid agent_id
        """
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        # Check max agents
        agents_dir = Path(root_path) / ".ai" / "db" / "agents"
        if agents_dir.exists():
            existing = [d.name for d in agents_dir.iterdir() if d.is_dir()]
            if len(existing) >= cls.MAX_AGENTS_PER_PROJECT and agent_id not in existing:
                raise ValueError(
                    f"Max {cls.MAX_AGENTS_PER_PROJECT} agents per project. "
                    f"Existing: {existing}"
                )

        # Create the storage manager which will create the structure
        manager = cls(root_path, agent_id=agent_id)

        # Write agent-level meta
        meta_path = manager.db_path / "_meta.json"
        meta = manager._read_json(meta_path) or {}
        meta.update({
            "agent_id": agent_id,
            "project_mode": "multi",
            "initialized_at": datetime.now().isoformat(),
            "version": "7.0.0"
        })
        manager._write_json(meta_path, meta)

        return manager

    def clear_all(self, confirm: bool = False):
        """
        Clear all data. Requires explicit confirmation.

        Args:
            confirm: Must be True to actually clear data
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to clear all data")

        # Clear threads
        for f in (self.db_path / "threads").glob("*.json"):
            f.unlink()

        # Clear bridges
        for f in (self.db_path / "bridges").glob("*.json"):
            f.unlink()

        # Reset meta
        self._ensure_structure()
