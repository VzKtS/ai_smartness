"""
Compactor - Memory compaction logic for AI Smartness.

Extracted from mcp/server.py do_compact() to be reusable
by both the MCP server and the daemon's proactive compaction.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from ..storage.manager import StorageManager
from ..config import THREAD_LIMITS

logger = logging.getLogger(__name__)


COMPACTION_STRATEGIES = {
    "gentle": {
        "merge_threshold": 0.95,
        "archive_age_days": 7,
        "max_active_threads": 50,
        "weight_decay": 0.95
    },
    "normal": {
        "merge_threshold": 0.85,
        "archive_age_days": 3,
        "max_active_threads": 30,
        "weight_decay": 0.90
    },
    "aggressive": {
        "merge_threshold": 0.75,
        "archive_age_days": 1,
        "max_active_threads": 15,
        "weight_decay": 0.80
    }
}


class Compactor:
    """
    Memory compaction engine.

    Merges similar threads, archives old ones, applies weight decay,
    and enforces thread limits.
    """

    def __init__(self, storage: StorageManager):
        self.storage = storage

    def compact(self, strategy: str = "normal", dry_run: bool = False) -> dict:
        """
        Execute memory compaction.

        Args:
            strategy: Compaction strategy (gentle, normal, aggressive)
            dry_run: If True, report what would happen without executing

        Returns:
            Report dict with actions taken
        """
        if strategy not in COMPACTION_STRATEGIES:
            strategy = "normal"

        params = COMPACTION_STRATEGIES[strategy]

        # Rebuild indexes from disk to ensure consistency
        self.storage.threads.rebuild_indexes()

        report = {
            "strategy": strategy,
            "dry_run": dry_run,
            "actions": [],
            "before": {},
            "after": {}
        }

        threads = self.storage.threads.get_active()
        report["before"] = {
            "active_threads": len(threads),
            "total_weight": round(sum(t.weight for t in threads), 2)
        }

        # 1. Find and merge similar threads
        threads_with_embeddings = [t for t in threads if t.embedding and not t.split_locked]
        merged_ids = set()

        for i, t1 in enumerate(threads_with_embeddings):
            if t1.id in merged_ids:
                continue
            for t2 in threads_with_embeddings[i + 1:]:
                if t2.id in merged_ids or t2.split_locked:
                    continue
                e1 = np.array(t1.embedding)
                e2 = np.array(t2.embedding)
                sim = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-8))
                if sim >= params["merge_threshold"]:
                    if not dry_run:
                        self.storage.threads.merge(t1.id, t2.id)
                    merged_ids.add(t2.id)
                    report["actions"].append({
                        "action": "merge",
                        "survivor": t1.id,
                        "absorbed": t2.id,
                        "similarity": round(sim, 2)
                    })

        # 2. Archive old threads
        cutoff = datetime.now() - timedelta(days=params["archive_age_days"])
        for thread in threads:
            if thread.id in merged_ids:
                continue
            if thread.last_active < cutoff:
                if not dry_run:
                    thread.archive()
                    self.storage.threads.save(thread)
                report["actions"].append({
                    "action": "archive",
                    "thread": thread.id,
                    "reason": "age",
                    "days_inactive": (datetime.now() - thread.last_active).days
                })

        # 3. Apply weight decay
        if not dry_run:
            for thread in self.storage.threads.get_active():
                thread.weight *= params["weight_decay"]
                self.storage.threads.save(thread)

        # 4. Enforce thread limit
        remaining = self.storage.threads.get_active()
        if len(remaining) > params["max_active_threads"]:
            to_archive = sorted(remaining, key=lambda t: t.weight)
            excess = len(remaining) - params["max_active_threads"]
            for thread in to_archive[:excess]:
                if not dry_run:
                    thread.archive()
                    self.storage.threads.save(thread)
                report["actions"].append({
                    "action": "archive",
                    "thread": thread.id,
                    "reason": "capacity",
                    "weight": round(thread.weight, 2)
                })

        # 5. Unlock compaction-locked threads
        if not dry_run:
            unlocked = self.storage.threads.unlock_compacted()
            if unlocked > 0:
                report["actions"].append({
                    "action": "unlock",
                    "count": unlocked,
                    "reason": "compaction_complete"
                })

        # Final stats
        if not dry_run:
            final = self.storage.threads.get_active()
            report["after"] = {
                "active_threads": len(final),
                "total_weight": round(sum(t.weight for t in final), 2)
            }
        else:
            report["after"] = report["before"].copy()
            report["after"]["note"] = "dry_run - no changes made"

        merged = len([a for a in report["actions"] if a["action"] == "merge"])
        archived = len([a for a in report["actions"] if a["action"] == "archive"])
        logger.info(f"Compaction complete: strategy={strategy}, merged={merged}, archived={archived}")

        return report
