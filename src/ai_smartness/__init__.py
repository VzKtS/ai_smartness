"""
AI Smartness - Meta-cognition layer for LLM agents.

Architecture:
- Thread: Work unit (topic/subject)
- ThinkBridge: Semantic connection between threads
- Storage: JSON persistence
- Processing: LLM extraction + Embeddings
- Intelligence: Thread lifecycle + Gossip propagation
- GuardCode: Rule enforcement + Context injection
- Hooks: Claude Code integration
- MCP: Native agent tools via JSON-RPC

V5 Hybrid Enhancements:
- ai_suggestions(): Proactive memory optimization suggestions
- ai_compact(): On-demand memory compaction
- ai_focus()/ai_unfocus(): Guide hook injection priorities
- ai_pin(): High-priority content capture
- ai_rate_context(): Feedback loop for injection quality

V5.1 Full Context Continuity:
- Session State: Work context tracking for seamless resume
- User Profile: Persistent personalization (role, preferences, rules)
- Layered Injection: 5-layer priority context injection
- ai_profile(): Profile management tool

Usage:
    from ai_smartness import StorageManager, ThreadManager, GossipPropagator

    storage = StorageManager("/path/to/project/.ai/db")
    manager = ThreadManager(storage)
    gossip = GossipPropagator(storage)
"""

__version__ = "6.2.1"
__author__ = "AI Smartness Team"

# Models
from .models.thread import Thread, Message, ThreadStatus, OriginType
from .models.bridge import ThinkBridge, BridgeType, BridgeStatus

# Storage
from .storage.manager import StorageManager
from .storage.threads import ThreadStorage
from .storage.bridges import BridgeStorage
from .storage.heartbeat import (
    load_heartbeat,
    save_heartbeat,
    init_heartbeat,
    increment_beat,
    record_interaction,
    get_temporal_context,
    is_new_session,
    get_time_since_last,
    update_context_tokens,
    get_context_info
)

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
    # Heartbeat (v4.1) + Session (v4.2) + Context (v4.3)
    "load_heartbeat",
    "save_heartbeat",
    "init_heartbeat",
    "increment_beat",
    "record_interaction",
    "get_temporal_context",
    "is_new_session",
    "get_time_since_last",
    "update_context_tokens",
    "get_context_info",

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
