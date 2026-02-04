"""
Shared Cognition Models - AI Smartness v6

Models for inter-agent thread sharing and cross-agent bridges.
Implements the Shared Cognition Protocol for memory isolation with collaboration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional
import uuid


class SharedVisibility(Enum):
    """Who can see/subscribe to a shared thread."""
    NETWORK = "network"        # All agents in the MCP network
    RESTRICTED = "restricted"  # Only agents in allowed_agents list


class SharedStatus(Enum):
    """Shared thread lifecycle."""
    ACTIVE = "active"          # Available for subscription
    DEPRECATED = "deprecated"  # Still readable, no new subscriptions
    ARCHIVED = "archived"      # No longer accessible


class BridgeProposalStatus(Enum):
    """InterAgentBridge lifecycle."""
    PENDING = "pending"        # Awaiting acceptance
    ACTIVE = "active"          # Both parties agreed
    REJECTED = "rejected"      # Target agent declined
    EXPIRED = "expired"        # No response within TTL
    INVALIDATED = "invalidated"  # Marked as no longer valid


@dataclass
class SharedThread:
    """
    A published snapshot of a thread for inter-agent sharing.

    Key principle: This is a READ-ONLY COPY, not a live reference.
    The owner controls when updates are published.
    """

    # Identity
    id: str                          # "shared_{thread_id}_{hash}"
    source_thread_id: str            # Original private thread ID
    owner_agent_id: str              # Agent who published it

    # Content (snapshot - NOT live reference)
    title: str
    summary: str
    topics: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Optional: Full messages (opt-in, heavier payload)
    include_messages: bool = False
    messages_snapshot: Optional[List[dict]] = None  # Frozen copy if included

    # Visibility control
    visibility: SharedVisibility = SharedVisibility.NETWORK
    allowed_agents: List[str] = field(default_factory=list)  # For RESTRICTED

    # Versioning (owner controls when to publish updates)
    version: int = 1
    version_history: List[dict] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source_thread_updated_at: Optional[datetime] = None

    # Subscription tracking
    subscribers: List[str] = field(default_factory=list)

    # Status
    status: SharedStatus = SharedStatus.ACTIVE

    @classmethod
    def create(
        cls,
        source_thread_id: str,
        owner_agent_id: str,
        title: str,
        summary: str,
        topics: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        visibility: SharedVisibility = SharedVisibility.NETWORK,
        include_messages: bool = False,
        messages_snapshot: Optional[List[dict]] = None
    ) -> "SharedThread":
        """Create a new shared thread from a private thread."""
        now = datetime.now()
        hash_suffix = uuid.uuid4().hex[:8]

        return cls(
            id=f"shared_{source_thread_id}_{hash_suffix}",
            source_thread_id=source_thread_id,
            owner_agent_id=owner_agent_id,
            title=title,
            summary=summary,
            topics=topics or [],
            tags=tags or [],
            visibility=visibility,
            include_messages=include_messages,
            messages_snapshot=messages_snapshot,
            created_at=now,
            updated_at=now,
            source_thread_updated_at=now
        )

    def publish_update(
        self,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        topics: Optional[List[str]] = None,
        messages_snapshot: Optional[List[dict]] = None
    ):
        """
        Publish a new version of this shared thread.

        Only the owner should call this method.
        """
        # Record version history
        self.version_history.append({
            "version": self.version,
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
            "summary_preview": self.summary[:100] if self.summary else ""
        })

        # Update content
        if title:
            self.title = title
        if summary:
            self.summary = summary
        if topics is not None:
            self.topics = topics
        if messages_snapshot is not None:
            self.messages_snapshot = messages_snapshot
            self.include_messages = True

        # Increment version
        self.version += 1
        self.updated_at = datetime.now()
        self.source_thread_updated_at = datetime.now()

    def add_subscriber(self, agent_id: str) -> bool:
        """Add a subscriber to this shared thread."""
        if self.status != SharedStatus.ACTIVE:
            return False

        if self.visibility == SharedVisibility.RESTRICTED:
            if agent_id not in self.allowed_agents:
                return False

        if agent_id not in self.subscribers:
            self.subscribers.append(agent_id)
        return True

    def remove_subscriber(self, agent_id: str) -> bool:
        """Remove a subscriber from this shared thread."""
        if agent_id in self.subscribers:
            self.subscribers.remove(agent_id)
            return True
        return False

    def deprecate(self):
        """Mark as deprecated (no new subscriptions)."""
        self.status = SharedStatus.DEPRECATED
        self.updated_at = datetime.now()

    def archive(self):
        """Archive this shared thread (no longer accessible)."""
        self.status = SharedStatus.ARCHIVED
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "source_thread_id": self.source_thread_id,
            "owner_agent_id": self.owner_agent_id,
            "title": self.title,
            "summary": self.summary,
            "topics": self.topics,
            "tags": self.tags,
            "include_messages": self.include_messages,
            "messages_snapshot": self.messages_snapshot,
            "visibility": self.visibility.value,
            "allowed_agents": self.allowed_agents,
            "version": self.version,
            "version_history": self.version_history,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "source_thread_updated_at": self.source_thread_updated_at.isoformat() if self.source_thread_updated_at else None,
            "subscribers": self.subscribers,
            "status": self.status.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SharedThread":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            source_thread_id=data["source_thread_id"],
            owner_agent_id=data["owner_agent_id"],
            title=data["title"],
            summary=data["summary"],
            topics=data.get("topics", []),
            tags=data.get("tags", []),
            include_messages=data.get("include_messages", False),
            messages_snapshot=data.get("messages_snapshot"),
            visibility=SharedVisibility(data.get("visibility", "network")),
            allowed_agents=data.get("allowed_agents", []),
            version=data.get("version", 1),
            version_history=data.get("version_history", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            source_thread_updated_at=datetime.fromisoformat(data["source_thread_updated_at"]) if data.get("source_thread_updated_at") else None,
            subscribers=data.get("subscribers", []),
            status=SharedStatus(data.get("status", "active"))
        )


@dataclass
class Subscription:
    """
    Local subscription to a SharedThread from another agent.

    This is the subscriber's local cached copy (read-only).
    """

    id: str                      # "sub_{shared_id}_{subscriber_id}"
    shared_thread_id: str        # SharedThread being subscribed to
    subscriber_agent_id: str     # This agent's ID
    owner_agent_id: str          # Original owner

    # Local cached copy
    cached_title: str
    cached_summary: str
    cached_topics: List[str] = field(default_factory=list)
    cached_messages: Optional[List[dict]] = None

    # Sync state
    synced_version: int = 1
    last_sync_at: datetime = field(default_factory=datetime.now)

    # Usage tracking
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None

    # Status
    status: str = "active"       # "active" | "stale" | "unsubscribed"

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        shared_thread: SharedThread,
        subscriber_agent_id: str
    ) -> "Subscription":
        """Create a subscription from a SharedThread."""
        now = datetime.now()

        return cls(
            id=f"sub_{shared_thread.id}_{subscriber_agent_id}",
            shared_thread_id=shared_thread.id,
            subscriber_agent_id=subscriber_agent_id,
            owner_agent_id=shared_thread.owner_agent_id,
            cached_title=shared_thread.title,
            cached_summary=shared_thread.summary,
            cached_topics=shared_thread.topics.copy(),
            cached_messages=shared_thread.messages_snapshot.copy() if shared_thread.messages_snapshot else None,
            synced_version=shared_thread.version,
            last_sync_at=now,
            created_at=now
        )

    def sync_from(self, shared_thread: SharedThread):
        """Update local cache from shared thread."""
        self.cached_title = shared_thread.title
        self.cached_summary = shared_thread.summary
        self.cached_topics = shared_thread.topics.copy()
        self.cached_messages = shared_thread.messages_snapshot.copy() if shared_thread.messages_snapshot else None
        self.synced_version = shared_thread.version
        self.last_sync_at = datetime.now()
        self.status = "active"

    def is_stale(self, current_version: int) -> bool:
        """Check if local cache is outdated."""
        return self.synced_version < current_version

    def mark_stale(self):
        """Mark subscription as stale (needs sync)."""
        self.status = "stale"

    def record_access(self):
        """Record that this subscription was accessed."""
        self.access_count += 1
        self.last_accessed_at = datetime.now()

    def unsubscribe(self):
        """Mark as unsubscribed."""
        self.status = "unsubscribed"

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "shared_thread_id": self.shared_thread_id,
            "subscriber_agent_id": self.subscriber_agent_id,
            "owner_agent_id": self.owner_agent_id,
            "cached_title": self.cached_title,
            "cached_summary": self.cached_summary,
            "cached_topics": self.cached_topics,
            "cached_messages": self.cached_messages,
            "synced_version": self.synced_version,
            "last_sync_at": self.last_sync_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Subscription":
        """Deserialize from dictionary."""
        sub = cls(
            id=data["id"],
            shared_thread_id=data["shared_thread_id"],
            subscriber_agent_id=data["subscriber_agent_id"],
            owner_agent_id=data["owner_agent_id"],
            cached_title=data["cached_title"],
            cached_summary=data["cached_summary"],
            cached_topics=data.get("cached_topics", []),
            cached_messages=data.get("cached_messages"),
            synced_version=data.get("synced_version", 1),
            last_sync_at=datetime.fromisoformat(data["last_sync_at"]),
            access_count=data.get("access_count", 0),
            status=data.get("status", "active"),
            created_at=datetime.fromisoformat(data["created_at"])
        )
        if data.get("last_accessed_at"):
            sub.last_accessed_at = datetime.fromisoformat(data["last_accessed_at"])
        return sub


@dataclass
class InterAgentBridge:
    """
    Semantic connection between SharedThreads from different agents.

    Requires bilateral consent: proposed by one agent, accepted by the other.
    """

    # Identity
    id: str                      # "ibridge_{timestamp}_{hash}"

    # Connection (SharedThread IDs only - never private thread IDs)
    source_shared_id: str
    target_shared_id: str

    # Agents involved
    source_agent_id: str         # Owner of source SharedThread
    target_agent_id: str         # Owner of target SharedThread

    # Semantic relationship (reuses existing BridgeType values)
    relation_type: str           # "extends", "depends", "contradicts", etc.
    reason: str                  # LLM explanation of the connection
    shared_concepts: List[str] = field(default_factory=list)

    # Bilateral consent
    proposed_by: str = ""
    proposal_message: str = ""
    accepted_by: Optional[str] = None
    acceptance_message: Optional[str] = None
    rejection_reason: Optional[str] = None

    # Status
    status: BridgeProposalStatus = BridgeProposalStatus.PENDING

    # Weighting (same decay mechanics as ThinkBridge)
    confidence: float = 0.8
    weight: float = 1.0
    use_count: int = 0
    last_used: Optional[datetime] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    accepted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # TTL for pending proposals

    @classmethod
    def create(
        cls,
        source_shared_id: str,
        target_shared_id: str,
        source_agent_id: str,
        target_agent_id: str,
        relation_type: str,
        reason: str,
        proposed_by: str,
        proposal_message: str = "",
        shared_concepts: Optional[List[str]] = None,
        ttl_hours: int = 24
    ) -> "InterAgentBridge":
        """Create a new inter-agent bridge proposal."""
        now = datetime.now()
        hash_suffix = uuid.uuid4().hex[:8]

        return cls(
            id=f"ibridge_{now.strftime('%Y%m%d_%H%M%S')}_{hash_suffix}",
            source_shared_id=source_shared_id,
            target_shared_id=target_shared_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            relation_type=relation_type,
            reason=reason,
            shared_concepts=shared_concepts or [],
            proposed_by=proposed_by,
            proposal_message=proposal_message,
            created_at=now,
            expires_at=now + timedelta(hours=ttl_hours)
        )

    def accept(self, accepted_by: str, message: str = ""):
        """Accept the bridge proposal."""
        self.accepted_by = accepted_by
        self.acceptance_message = message
        self.status = BridgeProposalStatus.ACTIVE
        self.accepted_at = datetime.now()

    def reject(self, reason: str = ""):
        """Reject the bridge proposal."""
        self.rejection_reason = reason
        self.status = BridgeProposalStatus.REJECTED

    def check_expired(self) -> bool:
        """Check if proposal has expired."""
        if self.status != BridgeProposalStatus.PENDING:
            return False

        if self.expires_at and datetime.now() > self.expires_at:
            self.status = BridgeProposalStatus.EXPIRED
            return True
        return False

    def record_use(self):
        """Record that this bridge was used."""
        self.use_count += 1
        self.last_used = datetime.now()
        # Boost weight (Hebbian learning)
        self.weight = min(1.0, self.weight + 0.1)

    def invalidate(self, reason: str = ""):
        """Mark bridge as invalidated."""
        self.status = BridgeProposalStatus.INVALIDATED
        if reason:
            self.rejection_reason = reason

    def is_active(self) -> bool:
        """Check if bridge is active and usable."""
        return self.status == BridgeProposalStatus.ACTIVE

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "source_shared_id": self.source_shared_id,
            "target_shared_id": self.target_shared_id,
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "relation_type": self.relation_type,
            "reason": self.reason,
            "shared_concepts": self.shared_concepts,
            "proposed_by": self.proposed_by,
            "proposal_message": self.proposal_message,
            "accepted_by": self.accepted_by,
            "acceptance_message": self.acceptance_message,
            "rejection_reason": self.rejection_reason,
            "status": self.status.value,
            "confidence": self.confidence,
            "weight": self.weight,
            "use_count": self.use_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat(),
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InterAgentBridge":
        """Deserialize from dictionary."""
        bridge = cls(
            id=data["id"],
            source_shared_id=data["source_shared_id"],
            target_shared_id=data["target_shared_id"],
            source_agent_id=data["source_agent_id"],
            target_agent_id=data["target_agent_id"],
            relation_type=data["relation_type"],
            reason=data["reason"],
            shared_concepts=data.get("shared_concepts", []),
            proposed_by=data.get("proposed_by", ""),
            proposal_message=data.get("proposal_message", ""),
            accepted_by=data.get("accepted_by"),
            acceptance_message=data.get("acceptance_message"),
            rejection_reason=data.get("rejection_reason"),
            status=BridgeProposalStatus(data.get("status", "pending")),
            confidence=data.get("confidence", 0.8),
            weight=data.get("weight", 1.0),
            use_count=data.get("use_count", 0),
            created_at=datetime.fromisoformat(data["created_at"])
        )

        if data.get("last_used"):
            bridge.last_used = datetime.fromisoformat(data["last_used"])
        if data.get("accepted_at"):
            bridge.accepted_at = datetime.fromisoformat(data["accepted_at"])
        if data.get("expires_at"):
            bridge.expires_at = datetime.fromisoformat(data["expires_at"])

        return bridge

    def __repr__(self) -> str:
        return f"InterAgentBridge({self.source_agent_id}:{self.source_shared_id[:15]}... --[{self.relation_type}]--> {self.target_agent_id}:{self.target_shared_id[:15]}...)"
