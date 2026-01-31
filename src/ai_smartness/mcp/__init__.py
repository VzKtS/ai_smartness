"""
AI Smartness MCP Server

Exposes AI Smartness memory tools via Model Context Protocol (MCP).
This allows Claude Code agents to use native tools instead of hacked Read paths.

Tools:
- ai_recall: Semantic memory search
- ai_merge: Merge two threads
- ai_split: Split a drifted thread
- ai_unlock: Unlock a split-locked thread
- ai_help: Documentation
- ai_status: Memory status
"""

from .server import main as run_server

__all__ = ["run_server"]
