"""
SharedStorage - CRUD operations for Shared Cognition entities.

Handles storage for SharedThread, Subscription, and InterAgentBridge.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from ..models.shared import (
    SharedThread,
    Subscription,
    InterAgentBridge,
    SharedStatus,
    BridgeProposalStatus
)


class SharedStorage:
    """
    Storage layer for Shared Cognition entities.

    Directory structure:
    ~/.ai_smartness/shared/
    ├── published/        # SharedThreads I've published
    ├── subscriptions/    # SharedThreads I'm subscribed to
    ├── cross_bridges/    # InterAgentBridges
    ├── proposals/        # Pending bridge proposals
    │   ├── outgoing/     # Proposals I've sent
    │   └── incoming/     # Proposals I've received
    └── index.json        # Quick lookup index
    """

    def __init__(self, shared_path: Path):
        """
        Initialize shared storage.

        Args:
            shared_path: Path to shared directory (~/.ai_smartness/shared/)
        """
        self.path = Path(shared_path)
        self._setup_directories()
        self._ensure_index()

    def _setup_directories(self):
        """Create directory structure."""
        dirs = [
            self.path,
            self.path / "published",
            self.path / "subscriptions",
            self.path / "cross_bridges",
            self.path / "proposals" / "outgoing",
            self.path / "proposals" / "incoming"
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _ensure_index(self):
        """Ensure index file exists."""
        index_path = self.path / "index.json"
        if not index_path.exists():
            self._write_json(index_path, {
                "published": [],
                "subscriptions": [],
                "bridges": [],
                "last_updated": datetime.now().isoformat()
            })

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

    # =========================================================================
    # SHARED THREADS (Published by this agent)
    # =========================================================================

    def _published_path(self, shared_id: str) -> Path:
        """Get path for a published shared thread."""
        return self.path / "published" / f"{shared_id}.json"

    def save_published(self, shared_thread: SharedThread) -> SharedThread:
        """Save a shared thread that this agent published."""
        self._write_json(
            self._published_path(shared_thread.id),
            shared_thread.to_dict()
        )
        self._update_index("published", shared_thread.id, add=True)
        return shared_thread

    def get_published(self, shared_id: str) -> Optional[SharedThread]:
        """Get a published shared thread by ID."""
        data = self._read_json(self._published_path(shared_id))
        if data is None:
            return None
        return SharedThread.from_dict(data)

    def delete_published(self, shared_id: str) -> bool:
        """Delete a published shared thread."""
        path = self._published_path(shared_id)
        if not path.exists():
            return False
        path.unlink()
        self._update_index("published", shared_id, add=False)
        return True

    def get_all_published(self) -> List[SharedThread]:
        """Get all shared threads published by this agent."""
        threads = []
        for path in (self.path / "published").glob("shared_*.json"):
            thread = self.get_published(path.stem)
            if thread:
                threads.append(thread)
        return threads

    def get_published_by_status(self, status: SharedStatus) -> List[SharedThread]:
        """Get published threads by status."""
        return [t for t in self.get_all_published() if t.status == status]

    # =========================================================================
    # SUBSCRIPTIONS (Threads this agent is subscribed to)
    # =========================================================================

    def _subscription_path(self, sub_id: str) -> Path:
        """Get path for a subscription."""
        return self.path / "subscriptions" / f"{sub_id}.json"

    def save_subscription(self, subscription: Subscription) -> Subscription:
        """Save a subscription."""
        self._write_json(
            self._subscription_path(subscription.id),
            subscription.to_dict()
        )
        self._update_index("subscriptions", subscription.id, add=True)
        return subscription

    def get_subscription(self, sub_id: str) -> Optional[Subscription]:
        """Get a subscription by ID."""
        data = self._read_json(self._subscription_path(sub_id))
        if data is None:
            return None
        return Subscription.from_dict(data)

    def get_subscription_by_shared_id(self, shared_thread_id: str, agent_id: str) -> Optional[Subscription]:
        """Get subscription for a specific shared thread."""
        sub_id = f"sub_{shared_thread_id}_{agent_id}"
        return self.get_subscription(sub_id)

    def delete_subscription(self, sub_id: str) -> bool:
        """Delete a subscription."""
        path = self._subscription_path(sub_id)
        if not path.exists():
            return False
        path.unlink()
        self._update_index("subscriptions", sub_id, add=False)
        return True

    def get_all_subscriptions(self) -> List[Subscription]:
        """Get all subscriptions."""
        subs = []
        for path in (self.path / "subscriptions").glob("sub_*.json"):
            sub = self.get_subscription(path.stem)
            if sub:
                subs.append(sub)
        return subs

    def get_active_subscriptions(self) -> List[Subscription]:
        """Get active subscriptions only."""
        return [s for s in self.get_all_subscriptions() if s.status == "active"]

    def get_stale_subscriptions(self) -> List[Subscription]:
        """Get stale subscriptions that need sync."""
        return [s for s in self.get_all_subscriptions() if s.status == "stale"]

    # =========================================================================
    # INTER-AGENT BRIDGES
    # =========================================================================

    def _bridge_path(self, bridge_id: str) -> Path:
        """Get path for a cross-agent bridge."""
        return self.path / "cross_bridges" / f"{bridge_id}.json"

    def save_bridge(self, bridge: InterAgentBridge) -> InterAgentBridge:
        """Save an inter-agent bridge."""
        self._write_json(
            self._bridge_path(bridge.id),
            bridge.to_dict()
        )
        self._update_index("bridges", bridge.id, add=True)
        return bridge

    def get_bridge(self, bridge_id: str) -> Optional[InterAgentBridge]:
        """Get a bridge by ID."""
        data = self._read_json(self._bridge_path(bridge_id))
        if data is None:
            return None
        return InterAgentBridge.from_dict(data)

    def delete_bridge(self, bridge_id: str) -> bool:
        """Delete a bridge."""
        path = self._bridge_path(bridge_id)
        if not path.exists():
            return False
        path.unlink()
        self._update_index("bridges", bridge_id, add=False)
        return True

    def get_all_bridges(self) -> List[InterAgentBridge]:
        """Get all inter-agent bridges."""
        bridges = []
        for path in (self.path / "cross_bridges").glob("ibridge_*.json"):
            bridge = self.get_bridge(path.stem)
            if bridge:
                bridges.append(bridge)
        return bridges

    def get_active_bridges(self) -> List[InterAgentBridge]:
        """Get active bridges only."""
        return [b for b in self.get_all_bridges() if b.is_active()]

    def get_bridges_by_agent(self, agent_id: str) -> List[InterAgentBridge]:
        """Get bridges involving a specific agent."""
        return [
            b for b in self.get_all_bridges()
            if b.source_agent_id == agent_id or b.target_agent_id == agent_id
        ]

    # =========================================================================
    # BRIDGE PROPOSALS
    # =========================================================================

    def _proposal_path(self, proposal_id: str, direction: str) -> Path:
        """Get path for a proposal (outgoing or incoming)."""
        return self.path / "proposals" / direction / f"{proposal_id}.json"

    def save_outgoing_proposal(self, bridge: InterAgentBridge) -> InterAgentBridge:
        """Save an outgoing bridge proposal."""
        self._write_json(
            self._proposal_path(bridge.id, "outgoing"),
            bridge.to_dict()
        )
        return bridge

    def save_incoming_proposal(self, bridge: InterAgentBridge) -> InterAgentBridge:
        """Save an incoming bridge proposal."""
        self._write_json(
            self._proposal_path(bridge.id, "incoming"),
            bridge.to_dict()
        )
        return bridge

    def get_outgoing_proposals(self) -> List[InterAgentBridge]:
        """Get all outgoing proposals (pending)."""
        proposals = []
        for path in (self.path / "proposals" / "outgoing").glob("ibridge_*.json"):
            data = self._read_json(path)
            if data:
                bridge = InterAgentBridge.from_dict(data)
                # Check expiry
                if not bridge.check_expired():
                    if bridge.status == BridgeProposalStatus.PENDING:
                        proposals.append(bridge)
        return proposals

    def get_incoming_proposals(self) -> List[InterAgentBridge]:
        """Get all incoming proposals (pending)."""
        proposals = []
        for path in (self.path / "proposals" / "incoming").glob("ibridge_*.json"):
            data = self._read_json(path)
            if data:
                bridge = InterAgentBridge.from_dict(data)
                # Check expiry
                if not bridge.check_expired():
                    if bridge.status == BridgeProposalStatus.PENDING:
                        proposals.append(bridge)
        return proposals

    def delete_proposal(self, proposal_id: str, direction: str) -> bool:
        """Delete a proposal."""
        path = self._proposal_path(proposal_id, direction)
        if path.exists():
            path.unlink()
            return True
        return False

    def move_proposal_to_bridge(self, proposal_id: str, direction: str) -> Optional[InterAgentBridge]:
        """Move accepted proposal to bridges."""
        path = self._proposal_path(proposal_id, direction)
        data = self._read_json(path)
        if not data:
            return None

        bridge = InterAgentBridge.from_dict(data)
        if bridge.status == BridgeProposalStatus.ACTIVE:
            # Save as active bridge
            self.save_bridge(bridge)
            # Delete from proposals
            self.delete_proposal(proposal_id, direction)
            return bridge
        return None

    # =========================================================================
    # INDEX MANAGEMENT
    # =========================================================================

    def _update_index(self, category: str, item_id: str, add: bool = True):
        """Update the index file."""
        index_path = self.path / "index.json"
        index = self._read_json(index_path) or {
            "published": [],
            "subscriptions": [],
            "bridges": []
        }

        if add:
            if item_id not in index.get(category, []):
                if category not in index:
                    index[category] = []
                index[category].append(item_id)
        else:
            if item_id in index.get(category, []):
                index[category].remove(item_id)

        index["last_updated"] = datetime.now().isoformat()
        self._write_json(index_path, index)

    def get_stats(self) -> Dict[str, int]:
        """Get storage statistics."""
        return {
            "published_count": len(self.get_all_published()),
            "subscriptions_count": len(self.get_all_subscriptions()),
            "active_subscriptions": len(self.get_active_subscriptions()),
            "bridges_count": len(self.get_all_bridges()),
            "active_bridges": len(self.get_active_bridges()),
            "pending_outgoing": len(self.get_outgoing_proposals()),
            "pending_incoming": len(self.get_incoming_proposals())
        }

    # =========================================================================
    # SHARED COGNITION HYGIENE (v6.3)
    # =========================================================================

    def cleanup_orphans(self, thread_exists_fn=None) -> dict:
        """
        Clean up orphaned shared resources.

        Removes:
        1. Published SharedThreads whose source thread no longer exists
        2. Stale subscriptions (stale for > 24h)
        3. InterAgentBridges referencing dead SharedThreads
        4. Expired proposals from disk

        Args:
            thread_exists_fn: Callable(thread_id) -> bool to check if source thread exists.
                              If None, skips SharedThread orphan check.

        Returns:
            Report dict with counts of cleaned items
        """
        report = {
            "orphaned_shared_threads": 0,
            "stale_subscriptions": 0,
            "orphaned_bridges": 0,
            "expired_proposals": 0,
        }

        # 1. Published SharedThreads whose source thread no longer exists
        if thread_exists_fn:
            for shared_thread in self.get_all_published():
                if shared_thread.status == SharedStatus.ARCHIVED:
                    continue
                if not thread_exists_fn(shared_thread.source_thread_id):
                    shared_thread.archive()
                    self.save_published(shared_thread)
                    self.unpublish_from_network(shared_thread.id)
                    report["orphaned_shared_threads"] += 1

        # 2. Stale subscriptions (stale > 24h)
        now = datetime.now()
        for sub in self.get_all_subscriptions():
            if sub.status == "stale":
                hours_stale = (now - sub.last_sync_at).total_seconds() / 3600
                if hours_stale > 24:
                    self.delete_subscription(sub.id)
                    report["stale_subscriptions"] += 1
            elif sub.status == "unsubscribed":
                self.delete_subscription(sub.id)
                report["stale_subscriptions"] += 1

        # 3. InterAgentBridges referencing dead SharedThreads
        # Collect all known active shared thread IDs (local + network)
        active_shared_ids = set()
        for st in self.get_all_published():
            if st.status == SharedStatus.ACTIVE:
                active_shared_ids.add(st.id)
        # Also check network
        network_path = Path.home() / ".mcp_smartness" / "shared_threads"
        if network_path.exists():
            for path in network_path.glob("shared_*.json"):
                data = self._read_json(path)
                if data and data.get("status") == "active":
                    active_shared_ids.add(data.get("id", ""))

        for bridge in self.get_all_bridges():
            source_exists = bridge.source_shared_id in active_shared_ids
            target_exists = bridge.target_shared_id in active_shared_ids
            if not source_exists or not target_exists:
                self.delete_bridge(bridge.id)
                report["orphaned_bridges"] += 1

        # 4. Expired proposals on disk
        for direction in ["outgoing", "incoming"]:
            proposals_dir = self.path / "proposals" / direction
            for path in proposals_dir.glob("ibridge_*.json"):
                data = self._read_json(path)
                if not data:
                    continue
                bridge = InterAgentBridge.from_dict(data)
                if bridge.check_expired() or bridge.status in (
                    BridgeProposalStatus.REJECTED,
                    BridgeProposalStatus.EXPIRED,
                    BridgeProposalStatus.INVALIDATED
                ):
                    path.unlink()
                    report["expired_proposals"] += 1

        return report

    # =========================================================================
    # DISCOVERY (for finding shared threads from other agents)
    # =========================================================================

    # =========================================================================
    # USAGE TRACKING (Phase 3 - Cross-Agent Bridge Strength)
    # =========================================================================

    def record_bridge_cross_use(self, bridge_id: str, agent_id: str) -> bool:
        """Record cross-agent usage of a bridge."""
        bridge = self.get_bridge(bridge_id)
        if bridge and bridge.is_active():
            bridge.record_cross_agent_use(agent_id)
            self.save_bridge(bridge)
            return True
        return False

    def record_subscription_access(self, sub_id: str) -> bool:
        """Record access to a subscription (for recommendation scoring)."""
        sub = self.get_subscription(sub_id)
        if sub:
            sub.record_access()
            self.save_subscription(sub)
            return True
        return False

    # =========================================================================
    # TOPIC AGGREGATION (Phase 3 - Network-Wide Topic Discovery)
    # =========================================================================

    def get_network_topics(self) -> dict:
        """
        Aggregate topics from all shared threads in the network.

        Returns:
            Dict with topic_counts, agent_topics, trending
        """
        from collections import Counter

        network_path = Path.home() / ".mcp_smartness" / "shared_threads"
        if not network_path.exists():
            return {"topic_counts": {}, "agent_topics": {}, "total_threads": 0}

        topic_counts = Counter()
        agent_topics = {}
        total_threads = 0

        for path in network_path.glob("shared_*.json"):
            data = self._read_json(path)
            if not data:
                continue

            status = data.get("status", "active")
            if status != "active":
                continue

            total_threads += 1
            owner = data.get("owner_agent_id", "unknown")
            topics = data.get("topics", [])

            for topic in topics:
                topic_lower = topic.lower()
                topic_counts[topic_lower] += 1

                if owner not in agent_topics:
                    agent_topics[owner] = Counter()
                agent_topics[owner][topic_lower] += 1

        # Convert agent_topics counters to plain dicts
        agent_topics_dict = {
            agent: dict(counter.most_common(10))
            for agent, counter in agent_topics.items()
        }

        return {
            "topic_counts": dict(topic_counts.most_common(30)),
            "agent_topics": agent_topics_dict,
            "total_threads": total_threads
        }

    # =========================================================================
    # DISCOVERY (for finding shared threads from other agents)
    # =========================================================================

    def discover_shared_threads(
        self,
        topics: Optional[List[str]] = None,
        agent_id: Optional[str] = None,
        limit: int = 20
    ) -> List[SharedThread]:
        """
        Discover shared threads from the network.

        This reads from a shared network directory that all agents can access.
        In a real implementation, this would query a shared storage or
        use mcp_smartness for discovery.

        For now, we look in ~/.mcp_smartness/shared_threads/
        """
        network_path = Path.home() / ".mcp_smartness" / "shared_threads"
        if not network_path.exists():
            return []

        threads = []
        for path in network_path.glob("shared_*.json"):
            data = self._read_json(path)
            if data:
                thread = SharedThread.from_dict(data)

                # Filter by status
                if thread.status != SharedStatus.ACTIVE:
                    continue

                # Filter by agent if specified
                if agent_id and thread.owner_agent_id != agent_id:
                    continue

                # Filter by topics if specified
                if topics:
                    thread_topics = set(t.lower() for t in thread.topics)
                    search_topics = set(t.lower() for t in topics)
                    if not thread_topics & search_topics:
                        continue

                threads.append(thread)

        # Sort by update time (most recent first)
        threads.sort(key=lambda t: t.updated_at, reverse=True)
        return threads[:limit]

    def publish_to_network(self, shared_thread: SharedThread) -> bool:
        """
        Publish a shared thread to the network.

        This writes to a shared directory that other agents can discover.
        """
        network_path = Path.home() / ".mcp_smartness" / "shared_threads"
        network_path.mkdir(parents=True, exist_ok=True)

        file_path = network_path / f"{shared_thread.id}.json"
        self._write_json(file_path, shared_thread.to_dict())
        return True

    def unpublish_from_network(self, shared_id: str) -> bool:
        """Remove a shared thread from the network."""
        network_path = Path.home() / ".mcp_smartness" / "shared_threads"
        file_path = network_path / f"{shared_id}.json"

        if file_path.exists():
            file_path.unlink()
            return True
        return False
