"""
AI Smartness v2 - Meta-cognition layer for LLM agents.

Architecture:
- Thread: Work unit (topic/subject)
- ThinkBridge: Semantic connection between threads
- Storage: JSON persistence
- Processing: LLM extraction + Embeddings
- Intelligence: Thread lifecycle + Gossip propagation
- GuardCode: Rule enforcement + Context injection
- Hooks: Claude Code integration

Usage:
    from ai_smartness_v2 import StorageManager, ThreadManager, GossipPropagator

    storage = StorageManager("/path/to/project/.ai/db")
    manager = ThreadManager(storage)
    gossip = GossipPropagator(storage)
"""

__version__ = "2.5.0"
__author__ = "AI Smartness Team"

# Models
from .models.thread import Thread, Message, ThreadStatus, OriginType
from .models.bridge import ThinkBridge, BridgeType, BridgeStatus

# Storage
from .storage.manager import StorageManager
from .storage.threads import ThreadStorage
from .storage.bridges import BridgeStorage

# Processing
from .processing.extractor import LLMExtractor, Extraction, extract_title_from_content
from .processing.embeddings import EmbeddingManager, get_embedding_manager

# Intelligence
from .intelligence.thread_manager import ThreadManager, ThreadAction, ThreadDecision
from .intelligence.gossip import GossipPropagator, BridgeProposal
from .intelligence.synthesis import ContextSynthesizer, Synthesis

# GuardCode
from .guardcode.enforcer import (
    GuardCodeEnforcer,
    Rule,
    Reminder,
    RuleType,
    PlanModeRule,
    NoQuickSolutionsRule,
    PresentChoicesRule
)
from .guardcode.injector import ContextInjector, InjectionContext

# Config
from .config import Config, load_config, get_project_root

__all__ = [
    # Version
    "__version__",

    # Models
    "Thread",
    "Message",
    "ThreadStatus",
    "OriginType",
    "ThinkBridge",
    "BridgeType",
    "BridgeStatus",

    # Storage
    "StorageManager",
    "ThreadStorage",
    "BridgeStorage",

    # Processing
    "LLMExtractor",
    "Extraction",
    "extract_title_from_content",
    "EmbeddingManager",
    "get_embedding_manager",

    # Intelligence
    "ThreadManager",
    "ThreadAction",
    "ThreadDecision",
    "GossipPropagator",
    "BridgeProposal",
    "ContextSynthesizer",
    "Synthesis",

    # GuardCode
    "GuardCodeEnforcer",
    "Rule",
    "Reminder",
    "RuleType",
    "PlanModeRule",
    "NoQuickSolutionsRule",
    "PresentChoicesRule",
    "ContextInjector",
    "InjectionContext",

    # Config
    "Config",
    "load_config",
    "get_project_root"
]
