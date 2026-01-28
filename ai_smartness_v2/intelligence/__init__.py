"""Intelligence layer for AI Smartness v2."""

from .thread_manager import ThreadManager, ThreadAction, ThreadDecision
from .gossip import GossipPropagator, BridgeProposal
from .synthesis import ContextSynthesizer, Synthesis

__all__ = [
    "ThreadManager",
    "ThreadAction",
    "ThreadDecision",
    "GossipPropagator",
    "BridgeProposal",
    "ContextSynthesizer",
    "Synthesis"
]
