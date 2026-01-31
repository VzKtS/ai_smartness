"""Intelligence layer for AI Smartness."""

from .thread_manager import ThreadManager, ThreadAction, ThreadDecision
from .gossip import GossipPropagator, BridgeProposal
from .synthesis import ContextSynthesizer, Synthesis
from .memory_retriever import MemoryRetriever, get_memory_retriever

__all__ = [
    "ThreadManager",
    "ThreadAction",
    "ThreadDecision",
    "GossipPropagator",
    "BridgeProposal",
    "ContextSynthesizer",
    "Synthesis",
    "MemoryRetriever",
    "get_memory_retriever"
]
