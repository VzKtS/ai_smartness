"""
Thread model - Core entity for AI Smartness.

A Thread represents a work stream (subject/topic), not a temporal session.
Threads can be active, suspended, or archived.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import ClassVar, Dict, List, Optional
import uuid


class ThreadStatus(Enum):
    """Thread lifecycle status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class OriginType(Enum):
    """How the thread was created."""
    PROMPT = "prompt"
    FILE_READ = "file_read"
    TASK = "task"
    FETCH = "fetch"
    SPLIT = "split"
    REACTIVATION = "reactivation"


@dataclass
class Message:
    """A message within a thread."""
    id: str
    content: str
    source: str  # "user" or "assistant"
    timestamp: datetime
    metadata: dict = field(default_factory=dict)

    @classmethod
    def create(cls, content: str, source: str, **metadata) -> "Message":
        """Create a new message."""
        return cls(
            id=f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            content=content,
            source=source,
            timestamp=datetime.now(),
            metadata=metadata
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            source=data["source"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )


@dataclass
class Thread:
    """
    A Thread represents a work stream (subject/topic).

    Core entity in the neural network metaphor:
    - Thread = Neuron
    - ThinkBridge = Synapse

    Weight decay (neuronal dormancy):
    - weight decays over time based on last_active
    - threads below SUSPEND_THRESHOLD are auto-suspended
    - suspended threads can be reactivated when relevant
    - threads are NEVER deleted (unlike bridges)
    """
    # Decay constants (class-level, not instance fields)
    HALF_LIFE_DAYS: ClassVar[float] = 7.0       # Weight halves every 7 days without use
    SUSPEND_THRESHOLD: ClassVar[float] = 0.1    # Auto-suspend below this weight
    USE_BOOST: ClassVar[float] = 0.1            # Weight boost per activation

    # Mode quotas (class-level, not instance fields)
    MODE_QUOTAS: ClassVar[Dict[str, int]] = {
        "light": 15,
        "normal": 50,
        "heavy": 100,
        "max": 200
    }

    id: str
    title: str
    status: ThreadStatus

    # Content
    messages: List[Message] = field(default_factory=list)
    summary: str = ""

    # Origin and evolution
    origin_type: OriginType = OriginType.PROMPT
    drift_history: List[str] = field(default_factory=list)

    # Relationships
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)

    # Weighting (starts at 1.0, decays over time, boosted by usage)
    weight: float = 1.0
    last_active: datetime = field(default_factory=datetime.now)
    activation_count: int = 0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    topics: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Embeddings (populated by processing layer)
    embedding: Optional[List[float]] = None

    @classmethod
    def create(
        cls,
        title: str,
        origin_type: OriginType = OriginType.PROMPT,
        parent_id: Optional[str] = None
    ) -> "Thread":
        """Create a new thread."""
        now = datetime.now()
        return cls(
            id=f"thread_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            title=title,
            status=ThreadStatus.ACTIVE,
            origin_type=origin_type,
            drift_history=[origin_type.value],
            parent_id=parent_id,
            created_at=now,
            last_active=now
        )

    def add_message(self, content: str, source: str, **metadata) -> Message:
        """Add a message to the thread."""
        msg = Message.create(content, source, **metadata)
        self.messages.append(msg)
        self.activation_count += 1
        self.boost_weight()  # Hebbian reinforcement
        return msg

    def record_drift(self, new_origin: str):
        """Record a drift in the thread's focus."""
        if not self.drift_history or self.drift_history[-1] != new_origin:
            self.drift_history.append(new_origin)

    def suspend(self, reason: str = ""):
        """Suspend the thread."""
        self.status = ThreadStatus.SUSPENDED
        if reason:
            self.tags.append(f"suspended:{reason}")

    def archive(self):
        """Archive the thread (becomes a MemBloc equivalent)."""
        self.status = ThreadStatus.ARCHIVED

    def reactivate(self):
        """Reactivate a suspended or archived thread."""
        self.status = ThreadStatus.ACTIVE
        self.activation_count += 1
        self.record_drift("reactivation")
        self.boost_weight()  # Hebbian reinforcement

    def add_child(self, child_id: str):
        """Add a child thread reference."""
        if child_id not in self.child_ids:
            self.child_ids.append(child_id)

    def decay(self) -> bool:
        """
        Apply temporal decay to weight.

        Uses exponential decay with half-life.
        Unlike bridges, threads are suspended not deleted.

        Returns:
            True if thread should be suspended (weight < threshold)
        """
        now = datetime.now()
        hours_since = (now - self.last_active).total_seconds() / 3600
        days_since = hours_since / 24

        # Exponential decay: weight = weight * 0.5^(days/half_life)
        decay_factor = 0.5 ** (days_since / self.HALF_LIFE_DAYS)
        self.weight *= decay_factor

        # Check if should be suspended
        if self.weight < self.SUSPEND_THRESHOLD and self.status == ThreadStatus.ACTIVE:
            return True  # Should suspend

        return False  # Still active

    def should_suspend(self) -> bool:
        """Check if thread should be suspended based on weight."""
        return self.weight < self.SUSPEND_THRESHOLD and self.status == ThreadStatus.ACTIVE

    def boost_weight(self):
        """Boost weight when thread is used (Hebbian reinforcement)."""
        self.weight = min(1.0, self.weight + self.USE_BOOST)
        self.last_active = datetime.now()

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "messages": [m.to_dict() for m in self.messages],
            "summary": self.summary,
            "origin_type": self.origin_type.value,
            "drift_history": self.drift_history,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "weight": self.weight,
            "last_active": self.last_active.isoformat(),
            "activation_count": self.activation_count,
            "created_at": self.created_at.isoformat(),
            "topics": self.topics,
            "tags": self.tags,
            "embedding": self.embedding
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Thread":
        """Deserialize from dictionary."""
        thread = cls(
            id=data["id"],
            title=data["title"],
            status=ThreadStatus(data["status"]),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            summary=data.get("summary", ""),
            origin_type=OriginType(data.get("origin_type", "prompt")),
            drift_history=data.get("drift_history", []),
            parent_id=data.get("parent_id"),
            child_ids=data.get("child_ids", []),
            weight=data.get("weight", 0.5),
            last_active=datetime.fromisoformat(data["last_active"]),
            activation_count=data.get("activation_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            topics=data.get("topics", []),
            tags=data.get("tags", []),
            embedding=data.get("embedding")
        )
        return thread

    def __repr__(self) -> str:
        return f"Thread(id={self.id[:20]}..., title='{self.title[:30]}...', status={self.status.value})"
