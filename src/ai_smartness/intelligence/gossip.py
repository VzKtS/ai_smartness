"""
Gossip Propagation - ThinkBridge creation and propagation.

Implements the "gossip pattern" for spreading semantic connections
between threads based on embedding similarity and LLM reasoning.
"""

import json
import subprocess
from typing import List, Optional, Tuple
from dataclasses import dataclass

from ..models.thread import Thread
from ..models.bridge import ThinkBridge, BridgeType, BridgeStatus
from ..storage.manager import StorageManager
from ..processing.embeddings import get_embedding_manager


@dataclass
class BridgeProposal:
    """Proposed bridge between threads."""
    source_id: str
    target_id: str
    relation_type: BridgeType
    reason: str
    confidence: float
    shared_concepts: List[str]


class GossipPropagator:
    """
    Manages ThinkBridge creation and gossip propagation.

    Creates bridges based on:
    1. Embedding similarity (automatic)
    2. LLM reasoning (for complex relationships)
    3. Gossip propagation (spread through network)
    """

    def __init__(
        self,
        storage: StorageManager,
        similarity_threshold: float = 0.5,
        max_propagation_depth: int = 2
    ):
        """
        Initialize gossip propagator.

        Args:
            storage: StorageManager instance
            similarity_threshold: Minimum similarity for bridge creation
            max_propagation_depth: Maximum depth for gossip propagation
        """
        self.storage = storage
        self.similarity_threshold = similarity_threshold
        self.max_propagation_depth = max_propagation_depth
        self.embeddings = get_embedding_manager()

    def on_thread_modified(self, thread: Thread):
        """
        Called when a thread is modified.

        Checks for potential new bridges and propagates existing ones.

        Args:
            thread: The modified thread
        """
        # 1. Find potential bridges based on similarity
        proposals = self._find_bridge_candidates(thread)

        # 2. Create bridges that don't exist yet (bidirectional dedup)
        for proposal in proposals:
            existing_forward = self.storage.bridges.get_between(
                proposal.source_id,
                proposal.target_id
            )
            existing_reverse = self.storage.bridges.get_between(
                proposal.target_id,
                proposal.source_id
            )
            if not existing_forward and not existing_reverse:
                self._create_bridge(proposal)

        # 3. Propagate through existing bridges
        self._propagate_from_thread(thread)

    def _find_bridge_candidates(self, thread: Thread) -> List[BridgeProposal]:
        """Find active threads that should be bridged to this one."""
        if not thread.embedding:
            return []

        proposals = []
        all_threads = self.storage.threads.get_active()  # Only scan active threads

        for other in all_threads:
            if other.id == thread.id:
                continue

            if not other.embedding:
                continue

            # Calculate similarity
            similarity = self.embeddings.similarity(thread.embedding, other.embedding)

            if similarity >= self.similarity_threshold:
                # Determine relationship type
                relation_type = self._determine_relation_type(thread, other, similarity)

                # Find shared concepts
                shared = self._find_shared_concepts(thread, other)

                proposals.append(BridgeProposal(
                    source_id=thread.id,
                    target_id=other.id,
                    relation_type=relation_type,
                    reason=f"Embedding similarity: {similarity:.2f}",
                    confidence=similarity,
                    shared_concepts=shared
                ))

        return proposals

    def _determine_relation_type(
        self,
        source: Thread,
        target: Thread,
        similarity: float
    ) -> BridgeType:
        """
        Determine the type of relationship between threads.

        Uses heuristics based on thread properties.
        """
        # Check parent/child relationship
        if source.parent_id == target.id:
            return BridgeType.CHILD_OF

        if target.parent_id == source.id:
            return BridgeType.EXTENDS

        # Check if they share a parent (siblings)
        if source.parent_id and source.parent_id == target.parent_id:
            return BridgeType.SIBLING

        # Check creation times (newer might extend older)
        if source.created_at > target.created_at:
            return BridgeType.EXTENDS

        # Default based on similarity
        if similarity > 0.8:
            return BridgeType.EXTENDS
        else:
            return BridgeType.SIBLING

    def _find_shared_concepts(self, a: Thread, b: Thread) -> List[str]:
        """Find concepts shared between two threads."""
        a_topics = set(t.lower() for t in a.topics)
        b_topics = set(t.lower() for t in b.topics)
        return list(a_topics & b_topics)[:5]

    def _create_bridge(self, proposal: BridgeProposal) -> ThinkBridge:
        """Create a bridge from a proposal."""
        bridge = ThinkBridge.create(
            source_id=proposal.source_id,
            target_id=proposal.target_id,
            relation_type=proposal.relation_type,
            reason=proposal.reason,
            confidence=proposal.confidence,
            shared_concepts=proposal.shared_concepts,
            created_by="gossip"
        )
        self.storage.bridges.save(bridge)
        return bridge

    def _propagate_from_thread(self, thread: Thread):
        """
        Propagate bridges through the network from a thread.

        Gossip pattern: if A-B and B-C, consider A-C.
        """
        # Get all bridges connected to this thread
        connected = self.storage.bridges.get_connected(thread.id)

        for bridge in connected:
            if bridge.propagation_depth >= self.max_propagation_depth:
                continue

            # Get the other end of the bridge
            other_id = bridge.target_id if bridge.source_id == thread.id else bridge.source_id
            other = self.storage.threads.get(other_id)

            if not other:
                continue

            # Get bridges from the other thread
            other_bridges = self.storage.bridges.get_connected(other_id)

            for other_bridge in other_bridges:
                # Get the third thread
                third_id = other_bridge.target_id if other_bridge.source_id == other_id else other_bridge.source_id

                if third_id == thread.id:
                    continue

                third = self.storage.threads.get(third_id)
                if not third:
                    continue

                # Check if bridge already exists (both directions)
                existing_fwd = self.storage.bridges.get_between(thread.id, third_id)
                existing_rev = self.storage.bridges.get_between(third_id, thread.id)
                if existing_fwd or existing_rev:
                    continue

                # Calculate similarity
                if thread.embedding and third.embedding:
                    similarity = self.embeddings.similarity(thread.embedding, third.embedding)

                    # Only create if above threshold (lower than direct)
                    if similarity >= self.similarity_threshold * 0.8:
                        # Create propagated bridge
                        propagated_bridge = ThinkBridge.create(
                            source_id=thread.id,
                            target_id=third_id,
                            relation_type=BridgeType.EXTENDS,
                            reason=f"Gossip propagation via {other.title[:30]}",
                            confidence=similarity * 0.9,  # Slight confidence reduction
                            shared_concepts=self._find_shared_concepts(thread, third),
                            created_by="gossip",
                            propagated_from=bridge.id
                        )
                        propagated_bridge.propagation_depth = bridge.propagation_depth + 1
                        self.storage.bridges.save(propagated_bridge)

    def get_bridge_network(self, thread_id: str, depth: int = 2) -> dict:
        """
        Get the bridge network around a thread.

        Args:
            thread_id: Center thread ID
            depth: How many hops to traverse

        Returns:
            Network structure for visualization/analysis
        """
        network = {
            "center": thread_id,
            "nodes": {},
            "edges": []
        }

        visited = set()
        to_visit = [(thread_id, 0)]

        while to_visit:
            current_id, current_depth = to_visit.pop(0)

            if current_id in visited:
                continue
            visited.add(current_id)

            thread = self.storage.threads.get(current_id)
            if not thread:
                continue

            network["nodes"][current_id] = {
                "title": thread.title,
                "status": thread.status.value,
                "weight": thread.weight
            }

            if current_depth >= depth:
                continue

            # Get connected bridges
            bridges = self.storage.bridges.get_connected(current_id)

            for bridge in bridges:
                if not bridge.is_valid():
                    continue

                network["edges"].append({
                    "source": bridge.source_id,
                    "target": bridge.target_id,
                    "type": bridge.relation_type.value,
                    "confidence": bridge.confidence
                })

                # Add next hop
                other_id = bridge.target_id if bridge.source_id == current_id else bridge.source_id
                if other_id not in visited:
                    to_visit.append((other_id, current_depth + 1))

        return network

    def strengthen_used_bridges(self, thread_ids: List[str]):
        """
        Strengthen bridges between recently used threads.

        Called when threads are accessed together in context.
        """
        for i, id_a in enumerate(thread_ids):
            for id_b in thread_ids[i + 1:]:
                bridge = self.storage.bridges.get_between(id_a, id_b)
                if bridge:
                    bridge.strengthen(0.05)
                    bridge.record_use()
                    self.storage.bridges.save(bridge)

    def weaken_unused_bridges(self, days_threshold: int = 7):
        """
        DEPRECATED: Use prune_dead_bridges() instead.

        Weaken bridges that haven't been used recently.
        Kept for backward compatibility.
        """
        # Just call the new decay-based pruning
        self.prune_dead_bridges()

    def prune_dead_bridges(self) -> int:
        """
        Apply decay and prune dead bridges.

        Implements synaptic pruning: bridges decay over time
        based on their half-life. Bridges that fall below the
        death threshold are deleted.

        Returns:
            Number of bridges pruned
        """
        return self.storage.bridges.prune_dead_bridges()

    def get_bridge_health(self) -> dict:
        """
        Get health statistics for the bridge network.

        Returns:
            Dict with weight stats and network metrics
        """
        stats = self.storage.bridges.get_weight_stats()
        all_bridges = self.storage.bridges.get_all()

        # Count by relation type
        by_type = {}
        for bridge in all_bridges:
            type_name = bridge.relation_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        # Count by status
        by_status = {}
        for bridge in all_bridges:
            status_name = bridge.status.value
            by_status[status_name] = by_status.get(status_name, 0) + 1

        return {
            "weight_stats": stats,
            "by_type": by_type,
            "by_status": by_status,
            "half_life_days": 1.0  # From ThinkBridge.HALF_LIFE_DAYS
        }
