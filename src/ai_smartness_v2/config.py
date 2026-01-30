"""
Configuration for AI Smartness v2.

Handles loading/saving config and provides typed access to settings.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal
from datetime import datetime


# LLM model mapping by mode
GUARDIAN_MODELS = {
    "light": "claude-haiku-3-5-20250620",
    "normal": "claude-sonnet-4-20250514",
    "heavy": "claude-opus-4-5-20250514",
    "max": "claude-opus-4-5-20250514"  # MAX mode uses Opus for quality
}

# Thread limits by mode
THREAD_LIMITS = {
    "light": 15,
    "normal": 50,
    "heavy": 100,
    "max": 200
}

# Default embedding model (local, free)
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class Config:
    """
    AI Smartness v2 configuration.

    Loaded from .ai/config.json, provides typed access.
    """
    # Project info
    project_name: str = "unnamed"
    language: Literal["en", "fr", "es"] = "en"
    version: str = "2.2.0"
    initialized_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Mode (determines Guardian LLM and thread limits)
    mode: Literal["light", "normal", "heavy", "max"] = "normal"

    # LLM settings
    extraction_model: str = "claude-haiku-3-5-20250620"  # Default to Haiku for extraction
    embedding_model: str = DEFAULT_EMBEDDING_MODEL

    # Capture settings
    auto_capture: bool = True

    # Thread settings
    active_threads_limit: int = 30

    # GuardCode settings
    enforce_plan_mode: bool = True
    warn_quick_solutions: bool = True
    require_all_choices: bool = True

    @classmethod
    def load(cls, config_path: Path) -> "Config":
        """
        Load config from JSON file.

        Args:
            config_path: Path to config.json

        Returns:
            Config instance
        """
        if not config_path.exists():
            return cls()

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return cls._from_dict(data)
        except (json.JSONDecodeError, IOError):
            return cls()

    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary."""
        settings = data.get("settings", {})
        llm = data.get("llm", {})
        guardcode = data.get("guardcode", {})

        mode = settings.get("thread_mode", "normal")

        return cls(
            project_name=data.get("project_name", "unnamed"),
            language=data.get("language", "en"),
            version=data.get("version", "2.2.0"),
            initialized_at=data.get("initialized_at", datetime.now().isoformat()),
            mode=mode,
            extraction_model=llm.get("extraction_model", GUARDIAN_MODELS.get(mode, GUARDIAN_MODELS["normal"])),
            embedding_model=llm.get("embedding_model", DEFAULT_EMBEDDING_MODEL),
            auto_capture=settings.get("auto_capture", True),
            active_threads_limit=settings.get("active_threads_limit", 30),
            enforce_plan_mode=guardcode.get("enforce_plan_mode", True),
            warn_quick_solutions=guardcode.get("warn_quick_solutions", True),
            require_all_choices=guardcode.get("require_all_choices", True)
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "version": self.version,
            "project_name": self.project_name,
            "language": self.language,
            "initialized_at": self.initialized_at,
            "settings": {
                "thread_mode": self.mode,
                "auto_capture": self.auto_capture,
                "active_threads_limit": self.active_threads_limit
            },
            "llm": {
                "extraction_model": self.extraction_model,
                "embedding_model": self.embedding_model,
                "guardian_model": GUARDIAN_MODELS.get(self.mode, GUARDIAN_MODELS["normal"])
            },
            "guardcode": {
                "enforce_plan_mode": self.enforce_plan_mode,
                "warn_quick_solutions": self.warn_quick_solutions,
                "require_all_choices": self.require_all_choices
            }
        }

    def save(self, config_path: Path):
        """
        Save config to JSON file.

        Args:
            config_path: Path to config.json
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = config_path.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            temp_path.rename(config_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    @property
    def guardian_model(self) -> str:
        """Get the Guardian LLM model for the current mode."""
        return GUARDIAN_MODELS.get(self.mode, GUARDIAN_MODELS["normal"])


def get_project_root() -> Optional[Path]:
    """
    Find the project root (directory containing ai_smartness-v2).

    Searches upward from current directory.

    Returns:
        Path to project root, or None if not found
    """
    current = Path.cwd()

    for parent in [current] + list(current.parents):
        if (parent / "ai_smartness-v2").exists():
            return parent
        if (parent / ".ai").exists():
            return parent

    return None


def load_config() -> Config:
    """
    Load config from the project root.

    Returns:
        Config instance (default if not found)
    """
    root = get_project_root()
    if root is None:
        return Config()

    # Try ai_smartness-v2/.ai/config.json first
    config_path = root / "ai_smartness-v2" / ".ai" / "config.json"
    if config_path.exists():
        return Config.load(config_path)

    # Fall back to .ai/config.json
    config_path = root / ".ai" / "config.json"
    return Config.load(config_path)
