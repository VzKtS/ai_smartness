"""
BridgeStorage - CRUD operations for ThinkBridge entities.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from ..models.bridge import ThinkBridge, BridgeStatus


class BridgeStorage:
    """
    Storage layer for ThinkBridge entities.

    Handles CRUD operations and indexing by source/target.
    """

    def __init__(self, bridges_path: Path):
        """
        Initialize bridge storage.

        Args:
            bridges_path: Path to bridges directory
        """
        self.path = Path(bridges_path)
        self.path.mkdir(parents=True, exist_ok=True)

        # Index file for fast lookup
        self._index_path = self.path / "_index.json"
        self._ensure_index()

    def _ensure_index(self):
        """Ensure index file exists."""
        if not self._index_path.exists():
            self._write_json(self._index_path, {
                "by_source": {},
                "by_target": {},
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

    def _bridge_path(self, bridge_id: str) -> Path:
        """Get path for a bridge file."""
        return self.path / f"{bridge_id}.json"

    def save(self, bridge: ThinkBridge) -> ThinkBridge:
        """
        Save a bridge to storage.

        Dedup: If a bridge already exists between the same two threads
        (in either direction), boost the existing one instead of creating
        a duplicate. Only applies to NEW bridges (not updates).

        Args:
            bridge: ThinkBridge to save

        Returns:
            The saved bridge (may be the existing one if dedup triggered)
        """
        bridge_path = self._bridge_path(bridge.id)

        # If this bridge ID already exists on disk, it's an update — save directly
        if not bridge_path.exists():
            # New bridge — check for bidirectional duplicates
            existing = self.get_between(bridge.source_id, bridge.target_id)
            if existing is None:
                existing = self.get_between(bridge.target_id, bridge.source_id)

            if existing is not None:
                # Duplicate found — boost existing instead of creating new
                existing.record_use()
                self._write_json(self._bridge_path(existing.id), existing.to_dict())
                return existing

        # Write bridge file
        self._write_json(bridge_path, bridge.to_dict())

        # Update index
        self._update_index(bridge)

        return bridge

    def get(self, bridge_id: str) -> Optional[ThinkBridge]:
        """
        Get a bridge by ID.

        Args:
            bridge_id: Bridge ID

        Returns:
            ThinkBridge if found, None otherwise
        """
        data = self._read_json(self._bridge_path(bridge_id))
        if data is None:
            return None
        return ThinkBridge.from_dict(data)

    def delete(self, bridge_id: str) -> bool:
        """
        Delete a bridge.

        Args:
            bridge_id: Bridge ID to delete

        Returns:
            True if deleted, False if not found
        """
        bridge = self.get(bridge_id)
        if bridge is None:
            return False

        path = self._bridge_path(bridge_id)
        path.unlink()
        self._remove_from_index(bridge)
        return True

    def get_by_source(self, source_id: str) -> List[ThinkBridge]:
        """Get all bridges originating from a thread."""
        index = self._read_json(self._index_path) or {}
        bridge_ids = index.get("by_source", {}).get(source_id, [])

        bridges = []
        for bid in bridge_ids:
            bridge = self.get(bid)
            if bridge and bridge.is_valid():
                bridges.append(bridge)
        return bridges

    def get_by_target(self, target_id: str) -> List[ThinkBridge]:
        """Get all bridges pointing to a thread."""
        index = self._read_json(self._index_path) or {}
        bridge_ids = index.get("by_target", {}).get(target_id, [])

        bridges = []
        for bid in bridge_ids:
            bridge = self.get(bid)
            if bridge and bridge.is_valid():
                bridges.append(bridge)
        return bridges

    def get_between(self, source_id: str, target_id: str) -> Optional[ThinkBridge]:
        """
        Get bridge between two specific threads.

        Args:
            source_id: Source thread ID
            target_id: Target thread ID

        Returns:
            ThinkBridge if exists, None otherwise
        """
        for bridge in self.get_by_source(source_id):
            if bridge.target_id == target_id:
                return bridge
        return None

    def get_connected(self, thread_id: str) -> List[ThinkBridge]:
        """
        Get all bridges connected to a thread (as source or target).

        Args:
            thread_id: Thread ID

        Returns:
            List of all bridges connected to this thread
        """
        bridges = []
        seen_ids = set()

        # Outgoing bridges
        for bridge in self.get_by_source(thread_id):
            if bridge.id not in seen_ids:
                bridges.append(bridge)
                seen_ids.add(bridge.id)

        # Incoming bridges
        for bridge in self.get_by_target(thread_id):
            if bridge.id not in seen_ids:
                bridges.append(bridge)
                seen_ids.add(bridge.id)

        return bridges

    def get_all(self) -> List[ThinkBridge]:
        """Get all bridges."""
        bridges = []
        for bridge_file in self.path.glob("bridge_*.json"):
            bridge = self.get(bridge_file.stem)
            if bridge:
                bridges.append(bridge)
        return bridges

    def get_active(self) -> List[ThinkBridge]:
        """Get all active (non-invalid) bridges."""
        return [b for b in self.get_all() if b.is_valid()]

    def get_alive(self) -> List[ThinkBridge]:
        """Get all alive bridges (weight above death threshold)."""
        return [b for b in self.get_all() if b.is_alive()]

    def prune_dead_bridges(self) -> int:
        """
        Apply decay and remove dead bridges.

        This implements synaptic pruning: bridges that haven't been
        used decay over time and eventually die.

        Returns:
            Number of bridges pruned (deleted)
        """
        all_bridges = self.get_all()
        pruned_count = 0

        for bridge in all_bridges:
            # Apply decay and check if should die
            should_die = bridge.decay()

            if should_die:
                # Bridge is dead, delete it
                self.delete(bridge.id)
                pruned_count += 1
            else:
                # Bridge survived, save updated weight
                self.save(bridge)

        return pruned_count

    def get_weight_stats(self) -> Dict[str, float]:
        """
        Get weight statistics for all bridges.

        Returns:
            Dict with min, max, avg, alive_count, dead_count
        """
        all_bridges = self.get_all()

        if not all_bridges:
            return {
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "alive_count": 0,
                "dead_count": 0,
                "total": 0
            }

        weights = [b.weight for b in all_bridges]
        alive = [b for b in all_bridges if b.is_alive()]

        return {
            "min": min(weights),
            "max": max(weights),
            "avg": sum(weights) / len(weights),
            "alive_count": len(alive),
            "dead_count": len(all_bridges) - len(alive),
            "total": len(all_bridges)
        }

    def _update_index(self, bridge: ThinkBridge):
        """Update index after bridge change."""
        index = self._read_json(self._index_path) or {
            "by_source": {},
            "by_target": {}
        }

        # Update by_source index
        if bridge.source_id not in index["by_source"]:
            index["by_source"][bridge.source_id] = []
        if bridge.id not in index["by_source"][bridge.source_id]:
            index["by_source"][bridge.source_id].append(bridge.id)

        # Update by_target index
        if bridge.target_id not in index["by_target"]:
            index["by_target"][bridge.target_id] = []
        if bridge.id not in index["by_target"][bridge.target_id]:
            index["by_target"][bridge.target_id].append(bridge.id)

        index["last_updated"] = datetime.now().isoformat()
        self._write_json(self._index_path, index)

    def _remove_from_index(self, bridge: ThinkBridge):
        """Remove a bridge from the index."""
        index = self._read_json(self._index_path) or {
            "by_source": {},
            "by_target": {}
        }

        # Remove from by_source
        if bridge.source_id in index["by_source"]:
            if bridge.id in index["by_source"][bridge.source_id]:
                index["by_source"][bridge.source_id].remove(bridge.id)

        # Remove from by_target
        if bridge.target_id in index["by_target"]:
            if bridge.id in index["by_target"][bridge.target_id]:
                index["by_target"][bridge.target_id].remove(bridge.id)

        index["last_updated"] = datetime.now().isoformat()
        self._write_json(self._index_path, index)
