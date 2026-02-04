"""Data models for AI Smartness."""

from .thread import Thread, Message, ThreadStatus
from .bridge import ThinkBridge, BridgeType
from .shared import (
    SharedThread,
    Subscription,
    InterAgentBridge,
    SharedVisibility,
    SharedStatus,
    BridgeProposalStatus
)

__all__ = [
    "Thread", "Message", "ThreadStatus",
    "ThinkBridge", "BridgeType",
    "SharedThread", "Subscription", "InterAgentBridge",
    "SharedVisibility", "SharedStatus", "BridgeProposalStatus"
]
