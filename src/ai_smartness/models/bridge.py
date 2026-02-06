"""
ThinkBridge model - Semantic connections between threads.

In the neural network metaphor:
- Thread = Neuron
- ThinkBridge = Synapse

ThinkBridges are created by LLM reasoning and propagate via gossip pattern.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import ClassVar, List, Optional
import uuid


class BridgeType(Enum):
    """Type of semantic relationship between threads."""
    EXTENDS = "extends"       # B extends/continues A
    CONTRADICTS = "contradicts"  # B contradicts A
    DEPENDS = "depends"       # B depends on A
    REPLACES = "replaces"     # B replaces/supersedes A
    CHILD_OF = "child_of"     # B is a subtopic of A
    SIBLING = "sibling"       # A and B share a parent topic


class BridgeStatus(Enum):
    """Bridge lifecycle status."""
    ACTIVE = "active"
    WEAK = "weak"       # Low confidence, may be removed
    INVALID = "invalid"  # Marked as incorrect


@dataclass
class ThinkBridge:
    """
    A semantic connection between two threads.

    Created by LLM reasoning, not hardcoded thresholds.
    Propagates via gossip pattern.

    Weight decay (synaptic pruning):
    - weight starts at confidence value
    - decays exponentially over time (half-life)
    - usage reinforces weight (Hebbian learning)
    - bridge dies when weight < DEATH_THRESHOLD
    """
    # Decay constants (class-level, not instance fields)
    HALF_LIFE_DAYS: ClassVar[float] = 1.0      # Weight halves every day without use
    DEATH_THRESHOLD: ClassVar[float] = 0.05    # Bridge dies below this weight
    USE_BOOST: ClassVar[float] = 0.1           # Weight boost per use

    id: str
    source_id: str
    target_id: str

    # Relationship
    relation_type: BridgeType
    reason: str  # LLM explanation of why this bridge exists
    shared_concepts: List[str] = field(default_factory=list)

    # Confidence (from LLM or embedding similarity)
    confidence: float = 0.8
    status: BridgeStatus = BridgeStatus.ACTIVE

    # Weight for decay/pruning (separate from confidence)
    weight: float = 1.0  # Starts at 1.0, decays over time

    # Propagation tracking
    propagated_from: Optional[str] = None  # Parent bridge ID if propagated
    propagation_depth: int = 0  # 0 = direct, 1+ = propagated

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "llm"  # "llm", "gossip", "user"
    last_used: Optional[datetime] = None
    use_count: int = 0

    @classmethod
    def create(
        cls,
        source_id: str,
        target_id: str,
        relation_type: BridgeType,
        reason: str,
        confidence: float = 0.8,
        shared_concepts: Optional[List[str]] = None,
        created_by: str = "llm",
        propagated_from: Optional[str] = None
    ) -> "ThinkBridge":
        """Create a new bridge with weight initialized from confidence."""
        now = datetime.now()
        return cls(
            id=f"bridge_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            reason=reason,
            confidence=confidence,
            shared_concepts=shared_concepts or [],
            weight=confidence,  # Initialize weight from confidence
            created_at=now,
            created_by=created_by,
            propagated_from=propagated_from,
            propagation_depth=1 if propagated_from else 0
        )

    def record_use(self):
        """
        Record that this bridge was used for context retrieval.

        Hebbian learning: usage reinforces the connection.
        """
        self.last_used = datetime.now()
        self.use_count += 1
        # Boost weight (capped at 1.0)
        self.weight = min(1.0, self.weight + self.USE_BOOST)
        # Ensure active status if previously weak
        if self.status == BridgeStatus.WEAK:
            self.status = BridgeStatus.ACTIVE

    def decay(self) -> bool:
        """
        Apply temporal decay to weight.

        Uses exponential decay with half-life.

        Returns:
            True if bridge should die (weight < threshold)
        """
        # Reference time: last_used or created_at
        reference = self.last_used if self.last_used else self.created_at

        # Calculate time since last activity
        hours_since = (datetime.now() - reference).total_seconds() / 3600
        days_since = hours_since / 24

        # Exponential decay: weight = weight * 0.5^(days/half_life)
        decay_factor = 0.5 ** (days_since / self.HALF_LIFE_DAYS)
        self.weight *= decay_factor

        # Update status based on weight
        if self.weight < self.DEATH_THRESHOLD:
            self.status = BridgeStatus.INVALID
            return True  # Should die
        elif self.weight < 0.3:
            self.status = BridgeStatus.WEAK

        return False  # Still alive

    def is_alive(self) -> bool:
        """Check if bridge is still alive (weight above threshold)."""
        return self.weight >= self.DEATH_THRESHOLD and self.status != BridgeStatus.INVALID

    def weaken(self):
        """Mark bridge as weak (low confidence)."""
        self.status = BridgeStatus.WEAK

    def invalidate(self, reason: str = ""):
        """Mark bridge as invalid."""
        self.status = BridgeStatus.INVALID
        if reason:
            self.reason = f"{self.reason} [INVALID: {reason}]"

    def strengthen(self, boost: float = 0.1):
        """Increase confidence (used when bridge proves useful)."""
        self.confidence = min(1.0, self.confidence + boost)
        if self.status == BridgeStatus.WEAK:
            self.status = BridgeStatus.ACTIVE

    def is_valid(self) -> bool:
        """Check if bridge is still valid for use."""
        return self.status != BridgeStatus.INVALID

    def is_bidirectional(self) -> bool:
        """Check if this relationship type is bidirectional."""
        return self.relation_type in [BridgeType.SIBLING, BridgeType.CONTRADICTS]

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "reason": self.reason,
            "shared_concepts": self.shared_concepts,
            "confidence": self.confidence,
            "weight": self.weight,
            "status": self.status.value,
            "propagated_from": self.propagated_from,
            "propagation_depth": self.propagation_depth,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "use_count": self.use_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThinkBridge":
        """Deserialize from dictionary with backward compatibility."""
        confidence = data.get("confidence", 0.8)
        # Backward compat: old bridges without weight get 0.5 (neutral)
        weight = data.get("weight", 0.5)
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=BridgeType(data["relation_type"]),
            reason=data["reason"],
            shared_concepts=data.get("shared_concepts", []),
            confidence=confidence,
            weight=weight,
            status=BridgeStatus(data.get("status", "active")),
            propagated_from=data.get("propagated_from"),
            propagation_depth=data.get("propagation_depth", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data.get("created_by", "llm"),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            use_count=data.get("use_count", 0)
        )

    def __repr__(self) -> str:
        return f"ThinkBridge({self.source_id[:10]}... --[{self.relation_type.value}]--> {self.target_id[:10]}...)"
