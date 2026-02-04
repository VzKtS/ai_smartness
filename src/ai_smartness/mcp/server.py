#!/usr/bin/env python3
"""
AI Smartness MCP Server v6.0

A local MCP server that exposes AI Smartness memory tools to Claude Code agents.
Runs as a subprocess communicating via stdio (JSON-RPC).

Core Tools:
- ai_recall: Semantic memory search
- ai_merge: Merge two threads
- ai_split: Split a drifted thread
- ai_unlock: Unlock a split-locked thread
- ai_help: Documentation
- ai_status: Memory status

V5 Hybrid Enhancement Tools:
- ai_suggestions: Proactive memory optimization suggestions
- ai_compact: On-demand memory compaction (gentle/normal/aggressive)
- ai_focus/ai_unfocus: Guide hook injection priorities
- ai_pin: High-priority content capture
- ai_rate_context: Feedback loop for injection quality

V5.1 Full Context Continuity:
- ai_profile: User profile management (role, preferences, rules)

V6 Shared Cognition (inter-agent collaboration):
- ai_share: Share a thread with the network
- ai_unshare: Remove thread from sharing
- ai_publish: Update shared snapshot
- ai_discover: Find shared threads from other agents
- ai_subscribe: Subscribe to a shared thread
- ai_unsubscribe: Unsubscribe from a shared thread
- ai_sync: Pull updates for subscriptions
- ai_shared_status: Get shared cognition status

Usage:
    python3 -m ai_smartness.mcp.server

Configure in .claude/settings.json:
    {
      "mcpServers": {
        "ai-smartness": {
          "command": "python3",
          "args": ["/path/to/ai_smartness/mcp/server.py"]
        }
      }
    }
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# Setup imports
def _setup_imports():
    """Setup import paths for package modules."""
    # Get package root (ai_smartness directory)
    script_path = Path(__file__).resolve()
    mcp_dir = script_path.parent
    package_dir = mcp_dir.parent
    package_parent = package_dir.parent

    # Add to path if not present
    for p in [str(package_parent), str(package_dir.parent.parent)]:
        if p not in sys.path:
            sys.path.insert(0, p)

_setup_imports()

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Create server instance
server = Server("ai-smartness")

# Logging
LOG_PATH = None

def init_logging(ai_path: Path):
    """Initialize logging to .ai/mcp.log"""
    global LOG_PATH
    LOG_PATH = ai_path / "mcp.log"

def log(message: str):
    """Log a message."""
    if LOG_PATH:
        try:
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass


def get_ai_path() -> Path:
    """
    Detect the .ai directory path.

    Searches:
    1. Current working directory
    2. CWD/ai_smartness/.ai
    3. Package relative path

    Returns:
        Path to .ai directory

    Raises:
        RuntimeError if not found
    """
    cwd = Path.cwd()

    # Check CWD/.ai (symlink case)
    ai_path = cwd / ".ai"
    if ai_path.exists():
        return ai_path.resolve()

    # Check CWD/ai_smartness/.ai
    ai_path = cwd / "ai_smartness" / ".ai"
    if ai_path.exists():
        return ai_path

    # Package relative
    script_path = Path(__file__).resolve()
    package_dir = script_path.parent.parent
    ai_path = package_dir / ".ai"
    if ai_path.exists():
        return ai_path

    raise RuntimeError(
        f"Cannot find .ai directory. CWD={cwd}, "
        "expected .ai or ai_smartness/.ai"
    )


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

TOOLS = [
    Tool(
        name="ai_recall",
        description="Search semantic memory for relevant threads, summaries, and bridges. Use to find context about previous work on a topic.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - keyword, topic, or thread_id (e.g., 'authentication', 'hooks', 'thread_abc123')"
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="ai_merge",
        description="Merge two threads to consolidate context. The survivor thread absorbs all messages, topics, and tags from the absorbed thread. Use when threads are redundant or related.",
        inputSchema={
            "type": "object",
            "properties": {
                "survivor_id": {
                    "type": "string",
                    "description": "Thread ID that will absorb the other and remain active"
                },
                "absorbed_id": {
                    "type": "string",
                    "description": "Thread ID to be absorbed (will be archived with tag 'merged_into:survivor_id')"
                }
            },
            "required": ["survivor_id", "absorbed_id"]
        }
    ),
    Tool(
        name="ai_split",
        description="Split a thread that has drifted into multiple topics. Two-step process: first call without confirm to see messages, then call with confirm=true to execute.",
        inputSchema={
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Thread ID to split"
                },
                "confirm": {
                    "type": "boolean",
                    "description": "False (default) = list messages with IDs, True = execute the split",
                    "default": False
                },
                "titles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Titles for the new threads (required when confirm=true)"
                },
                "message_groups": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "description": "Message IDs grouped by new thread - [[msg1, msg2], [msg3, msg4]] (required when confirm=true)"
                },
                "lock_mode": {
                    "type": "string",
                    "enum": ["compaction", "agent_release", "force"],
                    "description": "Split lock mode: 'compaction' (auto-unlock at compact), 'agent_release' (manual unlock), 'force' (never auto-unlock)",
                    "default": "compaction"
                }
            },
            "required": ["thread_id"]
        }
    ),
    Tool(
        name="ai_unlock",
        description="Remove split_lock from a thread, allowing it to be merged. Use after split when you want to allow re-merging.",
        inputSchema={
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Thread ID to unlock"
                }
            },
            "required": ["thread_id"]
        }
    ),
    Tool(
        name="ai_help",
        description="Get AI Smartness documentation with current memory stats. Shows all available commands and tips.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="ai_status",
        description="Get current memory status: thread counts, active/suspended, bridges, last activity.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    # V5: Hybrid Enhancement Tools
    Tool(
        name="ai_suggestions",
        description="Get proactive suggestions: merge candidates, split candidates, recall hints, and memory health. Use to optimize your memory state.",
        inputSchema={
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Optional current context/topic for targeted suggestions"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="ai_compact",
        description="Trigger memory compaction to reduce context pressure. Merges similar threads and archives old ones.",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy": {
                    "type": "string",
                    "enum": ["gentle", "normal", "aggressive"],
                    "description": "Compaction aggressiveness: gentle (>0.95 similarity), normal (>0.85), aggressive (>0.75)",
                    "default": "normal"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, show what would happen without executing",
                    "default": False
                }
            },
            "required": []
        }
    ),
    Tool(
        name="ai_focus",
        description="Signal focus on a topic. Hooks will prioritize related threads in context injection.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic keyword or thread_id to focus on"
                },
                "weight": {
                    "type": "number",
                    "description": "Priority weight 0.0-1.0 (default 0.8)",
                    "default": 0.8
                }
            },
            "required": ["topic"]
        }
    ),
    Tool(
        name="ai_unfocus",
        description="Remove focus on a topic, or clear all focus if no topic specified.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Specific topic to unfocus, or omit to clear all"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="ai_pin",
        description="Pin important content with elevated priority. Creates a high-weight thread that bypasses normal coherence checking.",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content to pin (will be stored as-is)"
                },
                "title": {
                    "type": "string",
                    "description": "Optional title (auto-generated if not provided)"
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional topic tags"
                },
                "weight_boost": {
                    "type": "number",
                    "description": "Additional weight 0.0-0.5 (default 0.3)",
                    "default": 0.3
                }
            },
            "required": ["content"]
        }
    ),
    Tool(
        name="ai_rate_context",
        description="Rate the usefulness of injected context. Affects future injection probability for this thread.",
        inputSchema={
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Thread ID that was injected"
                },
                "useful": {
                    "type": "boolean",
                    "description": "True if context was helpful, False if noise"
                },
                "reason": {
                    "type": "string",
                    "description": "Optional explanation"
                }
            },
            "required": ["thread_id", "useful"]
        }
    ),
    # V5.1: Full Context Continuity
    Tool(
        name="ai_profile",
        description="View or update user profile for personalized context injection. Stores role, preferences, and context rules.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["view", "set_role", "set_preference", "add_rule", "remove_rule"],
                    "description": "Action: view (show profile), set_role (developer/owner/user), set_preference, add_rule, remove_rule"
                },
                "key": {
                    "type": "string",
                    "description": "For set_role: role value. For set_preference: preference key. For add/remove_rule: the rule text."
                },
                "value": {
                    "type": "string",
                    "description": "For set_preference: the preference value"
                }
            },
            "required": ["action"]
        }
    ),
    # V5.1.2: Cleanup tool
    Tool(
        name="ai_cleanup",
        description="Fix threads and bridges with missing or invalid titles. Mode 'auto' uses heuristics, 'interactive' returns items for agent review.",
        inputSchema={
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["auto", "interactive"],
                    "default": "auto",
                    "description": "auto: fix with heuristics, interactive: return items for agent to analyze and rename"
                },
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true (auto mode only), show what would be fixed without making changes"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="ai_rename",
        description="Rename a thread with a new title. Use after ai_cleanup(mode='interactive') to fix problematic titles.",
        inputSchema={
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Thread ID to rename"
                },
                "new_title": {
                    "type": "string",
                    "description": "New title for the thread (max 60 chars)"
                }
            },
            "required": ["thread_id", "new_title"]
        }
    ),
    # V5.2: Batch operations
    Tool(
        name="ai_merge_batch",
        description="Merge multiple thread pairs in a single operation. More efficient than multiple ai_merge calls.",
        inputSchema={
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "description": "List of merge operations [{survivor_id, absorbed_id}, ...]",
                    "items": {
                        "type": "object",
                        "properties": {
                            "survivor_id": {"type": "string"},
                            "absorbed_id": {"type": "string"}
                        },
                        "required": ["survivor_id", "absorbed_id"]
                    }
                }
            },
            "required": ["operations"]
        }
    ),
    Tool(
        name="ai_rename_batch",
        description="Rename multiple threads in a single operation. More efficient than multiple ai_rename calls.",
        inputSchema={
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "description": "List of rename operations [{thread_id, new_title}, ...]",
                    "items": {
                        "type": "object",
                        "properties": {
                            "thread_id": {"type": "string"},
                            "new_title": {"type": "string"}
                        },
                        "required": ["thread_id", "new_title"]
                    }
                }
            },
            "required": ["operations"]
        }
    ),
    # V6: Shared Cognition Tools
    Tool(
        name="ai_share",
        description="Share a thread with other agents. Creates a read-only snapshot visible to the network.",
        inputSchema={
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Thread ID to share"
                },
                "visibility": {
                    "type": "string",
                    "enum": ["network", "restricted"],
                    "description": "Who can see: 'network' (all agents) or 'restricted' (specific agents)",
                    "default": "network"
                },
                "include_messages": {
                    "type": "boolean",
                    "description": "Include full message content (heavier payload)",
                    "default": False
                },
                "allowed_agents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Agent IDs allowed to subscribe (for restricted visibility)"
                }
            },
            "required": ["thread_id"]
        }
    ),
    Tool(
        name="ai_unshare",
        description="Remove a thread from sharing. Existing subscribers keep their cached copy.",
        inputSchema={
            "type": "object",
            "properties": {
                "shared_id": {
                    "type": "string",
                    "description": "Shared thread ID to unshare"
                }
            },
            "required": ["shared_id"]
        }
    ),
    Tool(
        name="ai_publish",
        description="Update the shared snapshot with current thread state. Subscribers can sync to get updates.",
        inputSchema={
            "type": "object",
            "properties": {
                "shared_id": {
                    "type": "string",
                    "description": "Shared thread ID to update"
                }
            },
            "required": ["shared_id"]
        }
    ),
    Tool(
        name="ai_discover",
        description="Discover shared threads from other agents.",
        inputSchema={
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by topics"
                },
                "agent_id": {
                    "type": "string",
                    "description": "Filter by owner agent"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 20)",
                    "default": 20
                }
            },
            "required": []
        }
    ),
    Tool(
        name="ai_subscribe",
        description="Subscribe to a shared thread from another agent. Creates a local read-only copy.",
        inputSchema={
            "type": "object",
            "properties": {
                "shared_id": {
                    "type": "string",
                    "description": "Shared thread ID to subscribe to"
                }
            },
            "required": ["shared_id"]
        }
    ),
    Tool(
        name="ai_unsubscribe",
        description="Unsubscribe from a shared thread.",
        inputSchema={
            "type": "object",
            "properties": {
                "shared_id": {
                    "type": "string",
                    "description": "Shared thread ID to unsubscribe from"
                }
            },
            "required": ["shared_id"]
        }
    ),
    Tool(
        name="ai_sync",
        description="Pull updates for subscribed threads. Syncs all or specific subscription.",
        inputSchema={
            "type": "object",
            "properties": {
                "shared_id": {
                    "type": "string",
                    "description": "Optional: specific shared thread to sync (omit for all)"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="ai_shared_status",
        description="Get status of shared cognition: published threads, subscriptions, bridges.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return list of available AI Smartness tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Execute an AI Smartness tool.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of TextContent with result
    """
    try:
        ai_path = get_ai_path()
        init_logging(ai_path)
        log(f"CALL {name} args={arguments}")

        result = await execute_tool(name, arguments, ai_path)
        log(f"RESULT {name} → {len(result)} chars")

        return [TextContent(type="text", text=result)]

    except Exception as e:
        error_msg = f"# Error\n\n{type(e).__name__}: {e}"
        log(f"ERROR {name}: {e}")
        return [TextContent(type="text", text=error_msg)]


async def execute_tool(name: str, arguments: dict, ai_path: Path) -> str:
    """
    Execute the actual tool logic.

    Args:
        name: Tool name
        arguments: Tool arguments
        ai_path: Path to .ai directory

    Returns:
        Result string
    """
    # Import handlers from recall.py
    from ai_smartness.hooks.recall import (
        handle_recall,
        handle_merge,
        handle_split_info,
        handle_split_confirm,
        handle_unlock,
        handle_help,
    )

    if name == "ai_recall":
        query = arguments.get("query", "")
        if not query:
            return "# Error\n\nMissing required parameter: query"
        return handle_recall(query, ai_path)

    elif name == "ai_merge":
        survivor_id = arguments.get("survivor_id", "")
        absorbed_id = arguments.get("absorbed_id", "")
        if not survivor_id or not absorbed_id:
            return "# Error\n\nMissing required parameters: survivor_id and absorbed_id"
        return handle_merge(survivor_id, absorbed_id, ai_path)

    elif name == "ai_split":
        thread_id = arguments.get("thread_id", "")
        if not thread_id:
            return "# Error\n\nMissing required parameter: thread_id"

        confirm = arguments.get("confirm", False)

        if not confirm:
            # Step 1: Get split info
            return handle_split_info(thread_id, ai_path)
        else:
            # Step 2: Execute split
            titles = arguments.get("titles", [])
            message_groups = arguments.get("message_groups", [])
            lock_mode = arguments.get("lock_mode", "compaction")

            if not titles or not message_groups:
                return "# Error\n\nWhen confirm=true, 'titles' and 'message_groups' are required"

            # Convert to params dict format expected by handle_split_confirm
            params = {
                "titles": ",".join(titles),
                "lock": lock_mode
            }
            for i, group in enumerate(message_groups):
                params[f"msgs_{i}"] = ",".join(group)

            return handle_split_confirm(thread_id, params, ai_path)

    elif name == "ai_unlock":
        thread_id = arguments.get("thread_id", "")
        if not thread_id:
            return "# Error\n\nMissing required parameter: thread_id"
        return handle_unlock(thread_id, ai_path)

    elif name == "ai_help":
        return handle_help(ai_path)

    elif name == "ai_status":
        return get_status(ai_path)

    # V5: Hybrid Enhancement Tools
    elif name == "ai_suggestions":
        context = arguments.get("context", "")
        return get_suggestions(ai_path, context)

    elif name == "ai_compact":
        strategy = arguments.get("strategy", "normal")
        dry_run = arguments.get("dry_run", False)
        return do_compact(ai_path, strategy, dry_run)

    elif name == "ai_focus":
        topic = arguments.get("topic", "")
        if not topic:
            return "# Error\n\nMissing required parameter: topic"
        weight = arguments.get("weight", 0.8)
        return set_focus(ai_path, topic, weight)

    elif name == "ai_unfocus":
        topic = arguments.get("topic")
        return clear_focus(ai_path, topic)

    elif name == "ai_pin":
        content = arguments.get("content", "")
        if not content:
            return "# Error\n\nMissing required parameter: content"
        title = arguments.get("title")
        topics = arguments.get("topics", [])
        weight_boost = arguments.get("weight_boost", 0.3)
        return pin_content(ai_path, content, title, topics, weight_boost)

    elif name == "ai_rate_context":
        thread_id = arguments.get("thread_id", "")
        useful = arguments.get("useful")
        if not thread_id or useful is None:
            return "# Error\n\nMissing required parameters: thread_id and useful"
        reason = arguments.get("reason")
        return rate_context(ai_path, thread_id, useful, reason)

    # V5.1: Profile management
    elif name == "ai_profile":
        action = arguments.get("action", "view")
        key = arguments.get("key")
        value = arguments.get("value")
        return handle_profile(ai_path, action, key, value)

    # V5.1.2: Cleanup tool
    elif name == "ai_cleanup":
        mode = arguments.get("mode", "auto")
        dry_run = arguments.get("dry_run", False)
        return cleanup_threads(ai_path, mode, dry_run)

    elif name == "ai_rename":
        thread_id = arguments.get("thread_id", "")
        new_title = arguments.get("new_title", "")
        if not thread_id or not new_title:
            return "# Error\n\nMissing required parameters: thread_id and new_title"
        return rename_thread(ai_path, thread_id, new_title)

    # V5.2: Batch operations
    elif name == "ai_merge_batch":
        operations = arguments.get("operations", [])
        if not operations:
            return "# Error\n\nMissing required parameter: operations"
        return merge_batch(ai_path, operations)

    elif name == "ai_rename_batch":
        operations = arguments.get("operations", [])
        if not operations:
            return "# Error\n\nMissing required parameter: operations"
        return rename_batch(ai_path, operations)

    # V6: Shared Cognition Tools
    elif name == "ai_share":
        thread_id = arguments.get("thread_id", "")
        if not thread_id:
            return "# Error\n\nMissing required parameter: thread_id"
        visibility = arguments.get("visibility", "network")
        include_messages = arguments.get("include_messages", False)
        allowed_agents = arguments.get("allowed_agents", [])
        return share_thread(ai_path, thread_id, visibility, include_messages, allowed_agents)

    elif name == "ai_unshare":
        shared_id = arguments.get("shared_id", "")
        if not shared_id:
            return "# Error\n\nMissing required parameter: shared_id"
        return unshare_thread(ai_path, shared_id)

    elif name == "ai_publish":
        shared_id = arguments.get("shared_id", "")
        if not shared_id:
            return "# Error\n\nMissing required parameter: shared_id"
        return publish_update(ai_path, shared_id)

    elif name == "ai_discover":
        topics = arguments.get("topics", [])
        agent_id = arguments.get("agent_id")
        limit = arguments.get("limit", 20)
        return discover_threads(ai_path, topics, agent_id, limit)

    elif name == "ai_subscribe":
        shared_id = arguments.get("shared_id", "")
        if not shared_id:
            return "# Error\n\nMissing required parameter: shared_id"
        return subscribe_thread(ai_path, shared_id)

    elif name == "ai_unsubscribe":
        shared_id = arguments.get("shared_id", "")
        if not shared_id:
            return "# Error\n\nMissing required parameter: shared_id"
        return unsubscribe_thread(ai_path, shared_id)

    elif name == "ai_sync":
        shared_id = arguments.get("shared_id")
        return sync_subscriptions(ai_path, shared_id)

    elif name == "ai_shared_status":
        return get_shared_status(ai_path)

    else:
        return f"# Error\n\nUnknown tool: {name}"


def get_status(ai_path: Path) -> str:
    """
    Get current memory status.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Status string
    """
    lines = ["# AI Smartness Status", ""]

    # Thread stats
    try:
        from ai_smartness.storage.threads import ThreadStorage
        db_path = ai_path / "db"
        storage = ThreadStorage(db_path / "threads")
        stats = storage.get_weight_stats()

        lines.append("## Threads")
        lines.append(f"- Active: {stats.get('active_count', 0)}")
        lines.append(f"- Suspended: {stats.get('suspended_count', 0)}")
        lines.append(f"- Archived: {stats.get('archived_count', 0)}")
        lines.append(f"- Total: {stats.get('total', 0)}")
        lines.append("")

    except Exception as e:
        lines.append(f"## Threads\nError: {e}\n")

    # Bridge stats
    try:
        from ai_smartness.storage.bridges import BridgeStorage
        db_path = ai_path / "db"
        bridge_storage = BridgeStorage(db_path / "bridges")
        bridge_count = len(bridge_storage.get_all())

        lines.append("## Bridges")
        lines.append(f"- Total: {bridge_count}")
        lines.append("")

    except Exception as e:
        lines.append(f"## Bridges\nError: {e}\n")

    # Context info
    try:
        heartbeat_path = ai_path / "heartbeat.json"
        if heartbeat_path.exists():
            data = json.loads(heartbeat_path.read_text())
            pct = data.get("context_percent", 0)
            threshold = data.get("compact_threshold", 95)

            lines.append("## Context")
            lines.append(f"- Used: {pct}%")
            lines.append(f"- Compact threshold: {threshold}%")
            lines.append("")

    except Exception:
        pass

    # Config info
    try:
        config_path = ai_path / "config.json"
        if config_path.exists():
            config = json.loads(config_path.read_text())
            mode = config.get("settings", {}).get("thread_mode", "normal")
            limit = config.get("settings", {}).get("active_threads_limit", 50)

            lines.append("## Configuration")
            lines.append(f"- Mode: {mode}")
            lines.append(f"- Thread limit: {limit}")
            lines.append("")

    except Exception:
        pass

    return "\n".join(lines)


# =============================================================================
# V5: HYBRID ENHANCEMENT IMPLEMENTATIONS
# =============================================================================

COMPACTION_STRATEGIES = {
    "gentle": {
        "merge_threshold": 0.95,
        "archive_age_days": 30,
        "max_active_threads": 50,
        "weight_decay": 0.95
    },
    "normal": {
        "merge_threshold": 0.85,
        "archive_age_days": 14,
        "max_active_threads": 30,
        "weight_decay": 0.90
    },
    "aggressive": {
        "merge_threshold": 0.75,
        "archive_age_days": 7,
        "max_active_threads": 15,
        "weight_decay": 0.80
    }
}


def get_suggestions(ai_path: Path, context: str = "") -> str:
    """Get proactive suggestions for memory optimization."""
    from ai_smartness.storage.threads import ThreadStorage
    from ai_smartness.processing.embeddings import get_embedding_manager
    import numpy as np

    db_path = ai_path / "db"
    storage = ThreadStorage(db_path / "threads")

    suggestions = {
        "merge_candidates": [],
        "split_candidates": [],
        "recall_hints": [],
        "health": {}
    }

    threads = storage.get_active()

    # 1. Find merge candidates (similarity > 0.85)
    threads_with_embeddings = [t for t in threads if t.embedding]
    for i, t1 in enumerate(threads_with_embeddings):
        for t2 in threads_with_embeddings[i+1:]:
            if t1.split_locked or t2.split_locked:
                continue
            # Cosine similarity
            e1 = np.array(t1.embedding)
            e2 = np.array(t2.embedding)
            sim = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-8))
            if sim > 0.85:
                common_topics = set(t1.topics) & set(t2.topics)
                suggestions["merge_candidates"].append({
                    "thread_a": t1.id,
                    "title_a": t1.title[:40],
                    "thread_b": t2.id,
                    "title_b": t2.title[:40],
                    "similarity": round(sim, 2),
                    "common_topics": list(common_topics)[:3],
                    "command": f"ai_merge(survivor_id='{t1.id}', absorbed_id='{t2.id}')"
                })

    # 2. Find split candidates (drift detected)
    for thread in threads:
        if len(thread.drift_history) > 3:
            unique_origins = set(thread.drift_history[-5:])
            if len(unique_origins) >= 3 and not thread.split_locked:
                suggestions["split_candidates"].append({
                    "thread_id": thread.id,
                    "title": thread.title[:40],
                    "message_count": len(thread.messages),
                    "drift_count": len(unique_origins),
                    "reason": "Multiple topic shifts detected",
                    "command": f"ai_split(thread_id='{thread.id}')"
                })

    # 3. Recall hints based on context
    if context:
        try:
            emb_manager = get_embedding_manager()
            context_emb = emb_manager.encode(context)

            for thread in threads:
                if thread.embedding and thread.activation_count == 0:
                    e = np.array(thread.embedding)
                    sim = float(np.dot(context_emb, e) / (np.linalg.norm(context_emb) * np.linalg.norm(e) + 1e-8))
                    if sim > 0.5:
                        topic = thread.topics[0] if thread.topics else thread.title[:20]
                        suggestions["recall_hints"].append({
                            "topic": topic,
                            "thread_id": thread.id,
                            "title": thread.title[:40],
                            "similarity": round(sim, 2),
                            "command": f"ai_recall(query='{topic}')"
                        })
        except Exception:
            pass

    # 4. Health metrics
    total_weight = sum(t.weight for t in threads)
    context_pressure = min(1.0, total_weight / 10.0)

    recommendation = "Healthy state, no action needed"
    if context_pressure > 0.8:
        recommendation = "High pressure - consider aggressive compaction"
    elif context_pressure > 0.6:
        recommendation = "Moderate pressure - consider merging similar threads"
    elif suggestions["merge_candidates"]:
        recommendation = f"Found {len(suggestions['merge_candidates'])} merge candidates"

    suggestions["health"] = {
        "active_threads": len(threads),
        "total_weight": round(total_weight, 2),
        "context_pressure": round(context_pressure, 2),
        "recommendation": recommendation
    }

    # Limit results
    suggestions["merge_candidates"] = suggestions["merge_candidates"][:5]
    suggestions["split_candidates"] = suggestions["split_candidates"][:3]
    suggestions["recall_hints"] = suggestions["recall_hints"][:3]

    return f"# AI Suggestions\n\n```json\n{json.dumps(suggestions, indent=2)}\n```"


def do_compact(ai_path: Path, strategy: str = "normal", dry_run: bool = False) -> str:
    """Execute memory compaction."""
    from ai_smartness.storage.threads import ThreadStorage
    from datetime import timedelta
    import numpy as np

    if strategy not in COMPACTION_STRATEGIES:
        strategy = "normal"

    params = COMPACTION_STRATEGIES[strategy]
    db_path = ai_path / "db"
    storage = ThreadStorage(db_path / "threads")

    report = {
        "strategy": strategy,
        "dry_run": dry_run,
        "actions": [],
        "before": {},
        "after": {}
    }

    threads = storage.get_active()
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
        for t2 in threads_with_embeddings[i+1:]:
            if t2.id in merged_ids or t2.split_locked:
                continue
            e1 = np.array(t1.embedding)
            e2 = np.array(t2.embedding)
            sim = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-8))
            if sim >= params["merge_threshold"]:
                if not dry_run:
                    storage.merge(t1.id, t2.id)
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
                storage.save(thread)
            report["actions"].append({
                "action": "archive",
                "thread": thread.id,
                "reason": "age",
                "days_inactive": (datetime.now() - thread.last_active).days
            })

    # 3. Apply weight decay
    if not dry_run:
        for thread in storage.get_active():
            thread.weight *= params["weight_decay"]
            storage.save(thread)

    # 4. Enforce thread limit
    remaining = storage.get_active()
    if len(remaining) > params["max_active_threads"]:
        to_archive = sorted(remaining, key=lambda t: t.weight)
        excess = len(remaining) - params["max_active_threads"]
        for thread in to_archive[:excess]:
            if not dry_run:
                thread.archive()
                storage.save(thread)
            report["actions"].append({
                "action": "archive",
                "thread": thread.id,
                "reason": "capacity",
                "weight": round(thread.weight, 2)
            })

    # 5. Unlock compaction-locked threads
    if not dry_run:
        unlocked = storage.unlock_compacted()
        if unlocked > 0:
            report["actions"].append({
                "action": "unlock",
                "count": unlocked,
                "reason": "compaction_complete"
            })

    # Final stats
    if not dry_run:
        final = storage.get_active()
        report["after"] = {
            "active_threads": len(final),
            "total_weight": round(sum(t.weight for t in final), 2)
        }
    else:
        report["after"] = report["before"].copy()
        report["after"]["note"] = "dry_run - no changes made"

    return f"# Compaction Report\n\n```json\n{json.dumps(report, indent=2)}\n```"


def set_focus(ai_path: Path, topic: str, weight: float = 0.8) -> str:
    """Set focus on a topic."""
    weight = max(0.0, min(1.0, weight))

    focus_path = ai_path / "focus.json"

    # Load existing focus
    focus_data = {"active_focus": [], "last_updated": ""}
    if focus_path.exists():
        try:
            focus_data = json.loads(focus_path.read_text())
        except Exception:
            pass

    # Remove existing focus on same topic
    focus_data["active_focus"] = [
        f for f in focus_data.get("active_focus", [])
        if f.get("topic") != topic
    ]

    # Add new focus
    focus_data["active_focus"].append({
        "topic": topic,
        "weight": weight,
        "set_at": datetime.now().isoformat()
    })
    focus_data["last_updated"] = datetime.now().isoformat()

    # Save
    focus_path.write_text(json.dumps(focus_data, indent=2))

    # Count affected threads
    from ai_smartness.storage.threads import ThreadStorage
    db_path = ai_path / "db"
    storage = ThreadStorage(db_path / "threads")
    threads = storage.get_active()

    affected = 0
    for t in threads:
        if topic.lower() in [tp.lower() for tp in t.topics]:
            affected += 1
        elif topic.lower() in t.title.lower():
            affected += 1
        elif topic == t.id:
            affected += 1

    return f"# Focus Set\n\nFocus on **{topic}** (weight={weight})\n\n{affected} threads will be prioritized."


def clear_focus(ai_path: Path, topic: Optional[str] = None) -> str:
    """Clear focus on a topic or all focus."""
    focus_path = ai_path / "focus.json"

    if not focus_path.exists():
        return "# Focus Cleared\n\nNo active focus to clear."

    focus_data = json.loads(focus_path.read_text())

    if topic:
        # Clear specific topic
        before = len(focus_data.get("active_focus", []))
        focus_data["active_focus"] = [
            f for f in focus_data.get("active_focus", [])
            if f.get("topic") != topic
        ]
        after = len(focus_data["active_focus"])
        removed = before - after
        message = f"Removed focus on **{topic}**" if removed else f"No focus on '{topic}' found"
    else:
        # Clear all
        count = len(focus_data.get("active_focus", []))
        focus_data["active_focus"] = []
        message = f"Cleared all focus ({count} topics)"

    focus_data["last_updated"] = datetime.now().isoformat()
    focus_path.write_text(json.dumps(focus_data, indent=2))

    return f"# Focus Cleared\n\n{message}"


def pin_content(ai_path: Path, content: str, title: Optional[str], topics: list, weight_boost: float) -> str:
    """Pin content as a high-priority thread."""
    from ai_smartness.storage.threads import ThreadStorage
    from ai_smartness.models.thread import Thread, OriginType, Message

    weight_boost = max(0.0, min(0.5, weight_boost))

    db_path = ai_path / "db"
    storage = ThreadStorage(db_path / "threads")

    # Generate title if not provided
    if not title:
        title = content[:50].replace('\n', ' ').strip()
        if len(content) > 50:
            title += "..."

    # Create thread
    thread = Thread.create(title=title, origin_type=OriginType.PROMPT)
    thread.add_message(content, source="agent_pin", source_type="pin")
    thread.topics = topics or []
    thread.weight = min(1.5, 1.0 + weight_boost)  # Allow above 1.0 for pinned
    thread.tags = ["pinned"]

    storage.save(thread)

    return f"# Content Pinned\n\nThread: `{thread.id}`\nTitle: {title}\nWeight: {thread.weight:.2f}\nTopics: {', '.join(topics) if topics else 'none'}"


def rate_context(ai_path: Path, thread_id: str, useful: bool, reason: Optional[str]) -> str:
    """Rate context usefulness."""
    from ai_smartness.storage.threads import ThreadStorage

    db_path = ai_path / "db"
    storage = ThreadStorage(db_path / "threads")

    thread = storage.get(thread_id)
    if not thread:
        return f"# Error\n\nThread not found: {thread_id}"

    old_score = thread.relevance_score
    thread.add_rating(useful, reason)
    new_score = thread.relevance_score

    storage.save(thread)

    rating_text = "useful" if useful else "not useful"
    direction = "↑" if new_score > old_score else "↓" if new_score < old_score else "="

    return f"# Context Rated\n\nThread: `{thread_id}`\nRating: {rating_text}\nRelevance: {old_score:.2f} {direction} {new_score:.2f}"


def handle_profile(ai_path: Path, action: str, key: Optional[str], value: Optional[str]) -> str:
    """
    V5.1: Handle user profile management.

    Args:
        ai_path: Path to .ai directory
        action: view, set_role, set_preference, add_rule, remove_rule
        key: Key for the action
        value: Value for the action

    Returns:
        Result string
    """
    from ai_smartness.models.session import load_user_profile, save_user_profile

    profile = load_user_profile(ai_path)

    if action == "view":
        lines = ["# User Profile", ""]

        # Identity
        lines.append("## Identity")
        lines.append(f"- Role: {profile.identity.get('role', 'user')}")
        lines.append(f"- Relationship: {profile.identity.get('relationship', 'user')}")
        if profile.identity.get('name'):
            lines.append(f"- Name: {profile.identity['name']}")
        lines.append("")

        # Preferences
        lines.append("## Preferences")
        for k, v in profile.preferences.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

        # Patterns
        if any(profile.patterns.values()):
            lines.append("## Patterns (learned)")
            if profile.patterns.get("active_hours"):
                lines.append(f"- Active hours: {', '.join(profile.patterns['active_hours'])}")
            if profile.patterns.get("common_tasks"):
                lines.append(f"- Common tasks: {', '.join(profile.patterns['common_tasks'])}")
            lines.append("")

        # Rules
        if profile.context_rules:
            lines.append("## Context Rules")
            for rule in profile.context_rules:
                lines.append(f"- {rule}")
            lines.append("")

        lines.append(f"*Created: {profile.created_at[:10]}*")
        lines.append(f"*Updated: {profile.updated_at[:10]}*")

        return "\n".join(lines)

    elif action == "set_role":
        if not key:
            return "# Error\n\nMissing key parameter. Use: set_role with key='developer|owner|user'"
        if key not in ["user", "developer", "owner"]:
            return f"# Error\n\nInvalid role: {key}. Use: developer, owner, or user"
        profile.set_role(key)
        save_user_profile(ai_path, profile)
        return f"# Profile Updated\n\nRole set to: {key}"

    elif action == "set_preference":
        if not key or not value:
            return "# Error\n\nMissing key and/or value parameters"
        if key not in profile.preferences:
            return f"# Error\n\nUnknown preference: {key}. Available: {', '.join(profile.preferences.keys())}"
        profile.set_preference(key, value)
        save_user_profile(ai_path, profile)
        return f"# Profile Updated\n\nPreference {key} set to: {value}"

    elif action == "add_rule":
        if not key:
            return "# Error\n\nMissing key parameter (the rule text)"
        profile.add_rule(key)
        save_user_profile(ai_path, profile)
        return f"# Profile Updated\n\nRule added: {key}"

    elif action == "remove_rule":
        if not key:
            return "# Error\n\nMissing key parameter (the rule text to remove)"
        if key not in profile.context_rules:
            return f"# Error\n\nRule not found: {key}"
        profile.remove_rule(key)
        save_user_profile(ai_path, profile)
        return f"# Profile Updated\n\nRule removed: {key}"

    else:
        return f"# Error\n\nUnknown action: {action}. Use: view, set_role, set_preference, add_rule, remove_rule"


def cleanup_threads(ai_path: Path, mode: str = "auto", dry_run: bool = False) -> str:
    """
    Fix threads and bridges with missing or invalid titles.

    Args:
        ai_path: Path to .ai directory
        mode: 'auto' = fix with heuristics, 'interactive' = return items for agent review
        dry_run: If True (auto mode only), show what would be fixed without making changes

    Returns:
        Cleanup report or list of items for review
    """
    from ai_smartness.processing.extractor import extract_title_from_content

    problematic_threads = []
    fixed_threads = []
    fixed_bridges = []
    errors = []

    # Titles that indicate extraction failed
    BAD_TITLES = ["Unknown", "Unknown topic", "Untitled", ""]

    # Find problematic threads
    threads_dir = ai_path / "db" / "threads"
    if threads_dir.exists():
        for f in threads_dir.glob("*.json"):
            # Skip index files (_active.json, _suspended.json) - these are system files
            if f.stem.startswith("_"):
                continue

            try:
                data = json.loads(f.read_text())
                title = data.get("title", "")
                thread_id = data.get("id", f.stem)

                # Check for problematic titles
                is_bad_title = title in BAD_TITLES or not title

                # Also check for very short/unhelpful titles (like "Cette")
                is_short_title = len(title) <= 5 and title not in BAD_TITLES

                if is_bad_title or is_short_title:
                    summary = data.get("summary", "")

                    # Try to get content from messages if no summary
                    if not summary:
                        messages = data.get("messages", [])
                        if messages:
                            summary = messages[0].get("content", "")[:200]

                    if mode == "interactive":
                        # Return for agent review
                        problematic_threads.append({
                            "thread_id": thread_id,
                            "current_title": title if title else "(empty)",
                            "summary": summary[:150] if summary else "(no content)",
                            "suggested_title": extract_title_from_content(summary) if summary else None,
                            "reason": "short_title" if is_short_title else "bad_title"
                        })
                    else:
                        # Auto mode - fix with heuristics
                        if summary:
                            new_title = extract_title_from_content(summary)
                            old_title = title if title else "(empty)"

                            if not dry_run:
                                data["title"] = new_title
                                f.write_text(json.dumps(data, indent=2, ensure_ascii=False))

                            fixed_threads.append({
                                "id": thread_id,
                                "old": old_title,
                                "new": new_title,
                                "summary_preview": summary[:50]
                            })
            except Exception as e:
                errors.append(f"thread {f.name}: {e}")

    # Fix bridges
    bridges_dir = ai_path / "db" / "bridges"
    if bridges_dir.exists():
        for f in bridges_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())

                # Check source and target titles
                source_title = data.get("source_title", "")
                target_title = data.get("target_title", "")
                description = data.get("description", "")
                modified = False

                if source_title in ["Unknown", "Unknown topic", "Untitled", ""] or not source_title:
                    if description:
                        new_title = extract_title_from_content(description)[:30]
                        if not dry_run:
                            data["source_title"] = new_title
                        fixed_bridges.append({
                            "id": data.get("id", f.stem),
                            "field": "source_title",
                            "old": source_title if source_title else "(empty)",
                            "new": new_title
                        })
                        modified = True

                if target_title in ["Unknown", "Unknown topic", "Untitled", ""] or not target_title:
                    if description:
                        new_title = extract_title_from_content(description)[:30]
                        if not dry_run:
                            data["target_title"] = new_title
                        fixed_bridges.append({
                            "id": data.get("id", f.stem),
                            "field": "target_title",
                            "old": target_title if target_title else "(empty)",
                            "new": new_title
                        })
                        modified = True

                if modified and not dry_run:
                    f.write_text(json.dumps(data, indent=2, ensure_ascii=False))

            except Exception as e:
                errors.append(f"bridge {f.name}: {e}")

    # Build report based on mode
    if mode == "interactive":
        # Interactive mode: return items for agent review
        lines = ["# AI Cleanup - Interactive Mode", ""]
        lines.append("Review the following threads and use `ai_rename(thread_id, new_title)` to fix them.")
        lines.append("")

        if problematic_threads:
            lines.append(f"## Threads to Review: {len(problematic_threads)}")
            lines.append("")

            for item in problematic_threads:
                lines.append(f"### `{item['thread_id']}`")
                lines.append(f"- **Current title**: \"{item['current_title']}\"")
                lines.append(f"- **Reason**: {item['reason']}")
                lines.append(f"- **Summary**: {item['summary']}")
                if item['suggested_title']:
                    lines.append(f"- **Suggested**: \"{item['suggested_title']}\"")
                lines.append("")
                lines.append(f"```")
                lines.append(f"ai_rename(thread_id='{item['thread_id']}', new_title='YOUR_TITLE')")
                lines.append(f"```")
                lines.append("")
        else:
            lines.append("No threads need review.")
            lines.append("")

        if errors:
            lines.append(f"## Errors: {len(errors)}")
            for err in errors:
                lines.append(f"- {err}")
    else:
        # Auto mode: show what was fixed
        lines = ["# AI Cleanup Report", ""]

        if dry_run:
            lines.append("**Mode: DRY RUN** (no changes made)")
            lines.append("")

        # Threads section
        lines.append(f"## Threads Fixed: {len(fixed_threads)}")
        lines.append("")

        if fixed_threads:
            for item in fixed_threads:
                lines.append(f"- `{item['id']}`")
                lines.append(f"  - Old: \"{item['old']}\"")
                lines.append(f"  - New: \"{item['new']}\"")
                lines.append(f"  - From: \"{item['summary_preview']}...\"")
                lines.append("")
        else:
            lines.append("No threads need fixing.")
            lines.append("")

        # Bridges section
        lines.append(f"## Bridges Fixed: {len(fixed_bridges)}")
        lines.append("")

        if fixed_bridges:
            for item in fixed_bridges:
                lines.append(f"- `{item['id']}` ({item['field']})")
                lines.append(f"  - Old: \"{item['old']}\"")
                lines.append(f"  - New: \"{item['new']}\"")
                lines.append("")
        else:
            lines.append("No bridges need fixing.")
            lines.append("")

        if errors:
            lines.append(f"## Errors: {len(errors)}")
            lines.append("")
            for err in errors:
                lines.append(f"- {err}")

    return "\n".join(lines)


def rename_thread(ai_path: Path, thread_id: str, new_title: str) -> str:
    """
    Rename a thread with a new title.

    Args:
        ai_path: Path to .ai directory
        thread_id: Thread ID to rename
        new_title: New title for the thread

    Returns:
        Confirmation message
    """
    # Truncate title to 60 chars
    new_title = new_title[:60]

    threads_dir = ai_path / "db" / "threads"
    if not threads_dir.exists():
        return "# Error\n\nThreads directory not found"

    # Find the thread file
    thread_file = None
    for f in threads_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            if data.get("id") == thread_id:
                thread_file = f
                break
        except:
            continue

    if not thread_file:
        # Try direct filename match
        direct_file = threads_dir / f"{thread_id}.json"
        if direct_file.exists():
            thread_file = direct_file
        else:
            return f"# Error\n\nThread not found: {thread_id}"

    try:
        data = json.loads(thread_file.read_text())
        old_title = data.get("title", "(empty)")
        data["title"] = new_title
        thread_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        return f"# Thread Renamed\n\n- **ID**: `{thread_id}`\n- **Old title**: \"{old_title}\"\n- **New title**: \"{new_title}\""

    except Exception as e:
        return f"# Error\n\nFailed to rename thread: {e}"


def merge_batch(ai_path: Path, operations: list) -> str:
    """
    Merge multiple thread pairs in a single operation.

    Args:
        ai_path: Path to .ai directory
        operations: List of {survivor_id, absorbed_id} dicts

    Returns:
        Batch result summary
    """
    from ai_smartness.hooks.recall import handle_merge

    results = []
    success_count = 0
    error_count = 0

    for op in operations:
        survivor_id = op.get("survivor_id", "")
        absorbed_id = op.get("absorbed_id", "")

        if not survivor_id or not absorbed_id:
            results.append({
                "status": "error",
                "error": "Missing survivor_id or absorbed_id",
                **op
            })
            error_count += 1
            continue

        try:
            result = handle_merge(survivor_id, absorbed_id, ai_path)
            if "Error" in result:
                results.append({
                    "status": "error",
                    "error": result.split("\n")[-1],
                    "survivor_id": survivor_id,
                    "absorbed_id": absorbed_id
                })
                error_count += 1
            else:
                results.append({
                    "status": "ok",
                    "survivor_id": survivor_id,
                    "absorbed_id": absorbed_id
                })
                success_count += 1
        except Exception as e:
            results.append({
                "status": "error",
                "error": str(e),
                "survivor_id": survivor_id,
                "absorbed_id": absorbed_id
            })
            error_count += 1

    # Build report
    lines = ["# Batch Merge Results", ""]
    lines.append(f"**Total:** {len(operations)} | **Success:** {success_count} | **Errors:** {error_count}")
    lines.append("")

    if success_count > 0:
        lines.append("## Successful Merges")
        for r in results:
            if r["status"] == "ok":
                lines.append(f"- `{r['absorbed_id']}` → `{r['survivor_id']}`")
        lines.append("")

    if error_count > 0:
        lines.append("## Errors")
        for r in results:
            if r["status"] == "error":
                lines.append(f"- `{r.get('absorbed_id', '?')}` → `{r.get('survivor_id', '?')}`: {r['error']}")
        lines.append("")

    return "\n".join(lines)


def rename_batch(ai_path: Path, operations: list) -> str:
    """
    Rename multiple threads in a single operation.

    Args:
        ai_path: Path to .ai directory
        operations: List of {thread_id, new_title} dicts

    Returns:
        Batch result summary
    """
    results = []
    success_count = 0
    error_count = 0

    for op in operations:
        thread_id = op.get("thread_id", "")
        new_title = op.get("new_title", "")

        if not thread_id or not new_title:
            results.append({
                "status": "error",
                "error": "Missing thread_id or new_title",
                **op
            })
            error_count += 1
            continue

        result = rename_thread(ai_path, thread_id, new_title)
        if "Error" in result:
            results.append({
                "status": "error",
                "error": result.split("\n")[-1],
                "thread_id": thread_id,
                "new_title": new_title
            })
            error_count += 1
        else:
            results.append({
                "status": "ok",
                "thread_id": thread_id,
                "new_title": new_title
            })
            success_count += 1

    # Build report
    lines = ["# Batch Rename Results", ""]
    lines.append(f"**Total:** {len(operations)} | **Success:** {success_count} | **Errors:** {error_count}")
    lines.append("")

    if success_count > 0:
        lines.append("## Successful Renames")
        for r in results:
            if r["status"] == "ok":
                lines.append(f"- `{r['thread_id']}` → \"{r['new_title']}\"")
        lines.append("")

    if error_count > 0:
        lines.append("## Errors")
        for r in results:
            if r["status"] == "error":
                lines.append(f"- `{r.get('thread_id', '?')}`: {r['error']}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# V6: SHARED COGNITION IMPLEMENTATIONS
# =============================================================================

_cached_agent_id: str = ""


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _get_ppid(pid: int):
    """Get parent PID of a process (Linux)."""
    try:
        status_path = Path(f"/proc/{pid}/status")
        if status_path.exists():
            for line in status_path.read_text().splitlines():
                if line.startswith("PPid:"):
                    return int(line.split()[1])
    except Exception:
        pass
    return None


def _is_ancestor_of(ancestor_pid: int, descendant_pid: int, max_depth: int = 10) -> bool:
    """Check if ancestor_pid is in the process tree above descendant_pid."""
    pid = descendant_pid
    for _ in range(max_depth):
        ppid = _get_ppid(pid)
        if ppid is None or ppid <= 1:
            return False
        if ppid == ancestor_pid:
            return True
        pid = ppid
    return False


def _resolve_agent_id(project_path: str = None) -> str:
    """
    Resolve agent ID using mcp_smartness v2.0 session registry.

    Strategy (aligned with mcp_smartness):
    1. Session registry (PID-based): ~/.mcp_smartness/sessions/server_*.json
    2. Project config: {cwd}/.mcp_smartness_agent
    3. Global config: ~/.mcp_smartness/current_agent.json
    4. Fallback: "unknown"

    ai_smartness is a read-only consumer of the session registry.
    """
    global _cached_agent_id
    if _cached_agent_id:
        return _cached_agent_id

    if project_path is None:
        project_path = str(Path.cwd())

    # Tier 1: Session registry (PID-based)
    sessions_dir = Path.home() / ".mcp_smartness" / "sessions"
    if sessions_dir.exists():
        candidates = []
        for session_file in sessions_dir.glob("server_*.json"):
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                server_pid = data.get("server_pid")
                if not server_pid or not _is_pid_alive(server_pid):
                    continue
                if data.get("project_path") == project_path:
                    candidates.append(data)
            except Exception:
                continue

        if len(candidates) == 1:
            _cached_agent_id = candidates[0].get("agent_id", "unknown")
            return _cached_agent_id

        if len(candidates) > 1:
            # Multiple sessions - use PPID matching
            my_pid = os.getpid()
            for data in candidates:
                parent_pid = data.get("parent_pid")
                if parent_pid and _is_ancestor_of(parent_pid, my_pid):
                    _cached_agent_id = data.get("agent_id", "unknown")
                    return _cached_agent_id
            _cached_agent_id = candidates[0].get("agent_id", "unknown")
            return _cached_agent_id

    # Tier 2: Project config file
    config_path = Path(project_path) / ".mcp_smartness_agent"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            agent_id = data.get("agent_id")
            if agent_id:
                _cached_agent_id = agent_id
                return _cached_agent_id
        except Exception:
            pass

    # Tier 3: Global config
    global_config = Path.home() / ".mcp_smartness" / "current_agent.json"
    if global_config.exists():
        try:
            data = json.loads(global_config.read_text(encoding="utf-8"))
            agent_id = data.get("agent_id")
            if agent_id:
                _cached_agent_id = agent_id
                return _cached_agent_id
        except Exception:
            pass

    return "unknown"


def get_agent_id() -> str:
    """Get current agent ID - aligned with mcp_smartness v2.0 resolution."""
    return _resolve_agent_id()


def get_shared_storage(ai_path: Path):
    """Get SharedStorage instance."""
    from ai_smartness.storage.shared import SharedStorage
    shared_path = ai_path / "shared"
    return SharedStorage(shared_path)


def notify_mcp_smartness(
    event_type: str,
    payload: dict,
    target_agent: str = None
) -> bool:
    """
    Send notification to mcp_smartness network.

    Args:
        event_type: Type of event (shared_thread, bridge_proposal, etc.)
        payload: Event data
        target_agent: Specific agent to notify (None for broadcast)

    Returns:
        True if notification sent successfully
    """
    import subprocess

    agent_id = get_agent_id()
    if agent_id == "unknown":
        return False

    # Check if auto_notify is enabled in config
    config_path = Path.cwd() / "ai_smartness" / ".ai" / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            if not config.get("settings", {}).get("shared_cognition", {}).get("auto_notify_mcp_smartness", True):
                return False
        except Exception:
            pass

    # Build notification message
    message = {
        "event": event_type,
        "from_agent": agent_id,
        "timestamp": datetime.now().isoformat(),
        **payload
    }

    try:
        # Use mcp_smartness CLI to send message
        mcp_smartness_path = Path.home() / ".mcp_smartness"
        if not mcp_smartness_path.exists():
            return False

        # Write message to outbox for async delivery
        outbox_path = mcp_smartness_path / "outbox"
        outbox_path.mkdir(parents=True, exist_ok=True)

        msg_file = outbox_path / f"{event_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        msg_data = {
            "type": "broadcast" if target_agent is None else "notify",
            "to": target_agent,
            "subject": f"[ai_smartness] {event_type}",
            "payload": message,
            "priority": "normal"
        }
        msg_file.write_text(json.dumps(msg_data, indent=2))
        return True

    except Exception:
        return False


def share_thread(
    ai_path: Path,
    thread_id: str,
    visibility: str = "network",
    include_messages: bool = False,
    allowed_agents: list = None
) -> str:
    """Share a thread with the network."""
    from ai_smartness.storage.threads import ThreadStorage
    from ai_smartness.models.shared import SharedThread, SharedVisibility

    # Get the thread
    db_path = ai_path / "db"
    thread_storage = ThreadStorage(db_path / "threads")
    thread = thread_storage.get(thread_id)

    if not thread:
        return f"# Error\n\nThread not found: {thread_id}"

    # Create shared thread
    agent_id = get_agent_id()
    vis = SharedVisibility.RESTRICTED if visibility == "restricted" else SharedVisibility.NETWORK

    messages_snapshot = None
    if include_messages:
        messages_snapshot = [m.to_dict() for m in thread.messages]

    shared = SharedThread.create(
        source_thread_id=thread_id,
        owner_agent_id=agent_id,
        title=thread.title,
        summary=thread.summary,
        topics=thread.topics,
        tags=thread.tags,
        visibility=vis,
        include_messages=include_messages,
        messages_snapshot=messages_snapshot
    )

    if allowed_agents:
        shared.allowed_agents = allowed_agents

    # Save to local storage
    shared_storage = get_shared_storage(ai_path)
    shared_storage.save_published(shared)

    # Publish to network
    shared_storage.publish_to_network(shared)

    # Notify mcp_smartness network
    notified = notify_mcp_smartness(
        "shared_thread_published",
        {
            "shared_id": shared.id,
            "title": shared.title,
            "topics": shared.topics,
            "visibility": visibility
        }
    )

    notification_status = " (network notified)" if notified else ""

    return f"""# Thread Shared{notification_status}

**Shared ID**: `{shared.id}`
**Source**: `{thread_id}`
**Title**: {shared.title}
**Visibility**: {visibility}
**Include Messages**: {include_messages}
**Owner**: {agent_id}

Other agents can now discover and subscribe to this thread."""


def unshare_thread(ai_path: Path, shared_id: str) -> str:
    """Remove a thread from sharing."""
    shared_storage = get_shared_storage(ai_path)

    shared = shared_storage.get_published(shared_id)
    if not shared:
        return f"# Error\n\nShared thread not found: {shared_id}"

    # Archive it
    shared.archive()
    shared_storage.save_published(shared)

    # Remove from network
    shared_storage.unpublish_from_network(shared_id)

    return f"""# Thread Unshared

**Shared ID**: `{shared_id}`
**Status**: Archived

Existing subscribers keep their cached copy but won't receive updates."""


def publish_update(ai_path: Path, shared_id: str) -> str:
    """Update the shared snapshot."""
    from ai_smartness.storage.threads import ThreadStorage

    shared_storage = get_shared_storage(ai_path)
    shared = shared_storage.get_published(shared_id)

    if not shared:
        return f"# Error\n\nShared thread not found: {shared_id}"

    # Get source thread
    db_path = ai_path / "db"
    thread_storage = ThreadStorage(db_path / "threads")
    thread = thread_storage.get(shared.source_thread_id)

    if not thread:
        return f"# Error\n\nSource thread no longer exists: {shared.source_thread_id}"

    # Update snapshot
    old_version = shared.version
    messages_snapshot = None
    if shared.include_messages:
        messages_snapshot = [m.to_dict() for m in thread.messages]

    shared.publish_update(
        title=thread.title,
        summary=thread.summary,
        topics=thread.topics,
        messages_snapshot=messages_snapshot
    )

    # Save
    shared_storage.save_published(shared)
    shared_storage.publish_to_network(shared)

    # Notify subscribers via mcp_smartness
    notified_count = 0
    for subscriber in shared.subscribers:
        if notify_mcp_smartness(
            "shared_thread_updated",
            {
                "shared_id": shared_id,
                "title": shared.title,
                "new_version": shared.version,
                "old_version": old_version
            },
            target_agent=subscriber
        ):
            notified_count += 1

    notification_status = f" ({notified_count} notified)" if notified_count > 0 else ""

    return f"""# Shared Thread Updated{notification_status}

**Shared ID**: `{shared_id}`
**Version**: {old_version} → {shared.version}
**Subscribers**: {len(shared.subscribers)}

Subscribers can sync to get the latest version."""


def discover_threads(
    ai_path: Path,
    topics: list = None,
    agent_id: str = None,
    limit: int = 20
) -> str:
    """Discover shared threads from the network."""
    shared_storage = get_shared_storage(ai_path)
    threads = shared_storage.discover_shared_threads(topics, agent_id, limit)

    if not threads:
        filter_info = ""
        if topics:
            filter_info += f" topics={topics}"
        if agent_id:
            filter_info += f" agent={agent_id}"
        return f"# No Shared Threads Found\n\nNo shared threads match your criteria.{filter_info}"

    lines = ["# Discovered Shared Threads", ""]
    lines.append(f"Found {len(threads)} shared thread(s):")
    lines.append("")

    for t in threads:
        lines.append(f"## `{t.id}`")
        lines.append(f"- **Title**: {t.title}")
        lines.append(f"- **Owner**: {t.owner_agent_id}")
        lines.append(f"- **Topics**: {', '.join(t.topics) if t.topics else 'none'}")
        lines.append(f"- **Version**: {t.version}")
        lines.append(f"- **Summary**: {t.summary[:100]}..." if len(t.summary) > 100 else f"- **Summary**: {t.summary}")
        lines.append(f"- **Subscribe**: `ai_subscribe(shared_id='{t.id}')`")
        lines.append("")

    return "\n".join(lines)


def subscribe_thread(ai_path: Path, shared_id: str) -> str:
    """Subscribe to a shared thread."""
    from ai_smartness.models.shared import Subscription

    shared_storage = get_shared_storage(ai_path)
    agent_id = get_agent_id()

    # Check if already subscribed
    existing = shared_storage.get_subscription_by_shared_id(shared_id, agent_id)
    if existing:
        return f"# Already Subscribed\n\nYou are already subscribed to `{shared_id}`.\nUse `ai_sync(shared_id='{shared_id}')` to get updates."

    # Find the shared thread in network
    threads = shared_storage.discover_shared_threads()
    shared = None
    for t in threads:
        if t.id == shared_id:
            shared = t
            break

    if not shared:
        return f"# Error\n\nShared thread not found: {shared_id}"

    # Check visibility
    from ai_smartness.models.shared import SharedVisibility
    if shared.visibility == SharedVisibility.RESTRICTED:
        if agent_id not in shared.allowed_agents:
            return f"# Error\n\nAccess denied. This thread is restricted to specific agents."

    # Create subscription
    sub = Subscription.create(shared, agent_id)
    shared_storage.save_subscription(sub)

    # Register as subscriber on the shared thread
    shared.add_subscriber(agent_id)
    shared_storage.publish_to_network(shared)

    return f"""# Subscribed

**Shared ID**: `{shared_id}`
**Title**: {shared.title}
**Owner**: {shared.owner_agent_id}
**Version**: {shared.version}

You now have a local copy. Use `ai_sync()` to pull updates."""


def unsubscribe_thread(ai_path: Path, shared_id: str) -> str:
    """Unsubscribe from a shared thread."""
    shared_storage = get_shared_storage(ai_path)
    agent_id = get_agent_id()

    sub = shared_storage.get_subscription_by_shared_id(shared_id, agent_id)
    if not sub:
        return f"# Error\n\nNot subscribed to: {shared_id}"

    sub.unsubscribe()
    shared_storage.save_subscription(sub)

    return f"""# Unsubscribed

**Shared ID**: `{shared_id}`

Your local cache is preserved but marked as unsubscribed."""


def sync_subscriptions(ai_path: Path, shared_id: str = None) -> str:
    """Sync subscribed threads."""
    shared_storage = get_shared_storage(ai_path)
    agent_id = get_agent_id()

    if shared_id:
        # Sync specific subscription
        sub = shared_storage.get_subscription_by_shared_id(shared_id, agent_id)
        if not sub:
            return f"# Error\n\nNot subscribed to: {shared_id}"

        # Find latest version
        threads = shared_storage.discover_shared_threads()
        shared = None
        for t in threads:
            if t.id == shared_id:
                shared = t
                break

        if not shared:
            sub.mark_stale()
            shared_storage.save_subscription(sub)
            return f"# Sync Failed\n\nShared thread no longer available: {shared_id}"

        if sub.synced_version >= shared.version:
            return f"# Already Up-to-Date\n\n`{shared_id}` is at version {shared.version}"

        old_version = sub.synced_version
        sub.sync_from(shared)
        shared_storage.save_subscription(sub)

        return f"""# Synced

**Shared ID**: `{shared_id}`
**Version**: {old_version} → {shared.version}"""

    else:
        # Sync all subscriptions
        subs = shared_storage.get_active_subscriptions()
        if not subs:
            return "# No Subscriptions\n\nYou have no active subscriptions to sync."

        threads = shared_storage.discover_shared_threads()
        threads_by_id = {t.id: t for t in threads}

        results = []
        for sub in subs:
            shared = threads_by_id.get(sub.shared_thread_id)
            if not shared:
                sub.mark_stale()
                shared_storage.save_subscription(sub)
                results.append(f"- `{sub.shared_thread_id}`: **stale** (no longer available)")
            elif sub.synced_version >= shared.version:
                results.append(f"- `{sub.shared_thread_id}`: up-to-date (v{shared.version})")
            else:
                old_v = sub.synced_version
                sub.sync_from(shared)
                shared_storage.save_subscription(sub)
                results.append(f"- `{sub.shared_thread_id}`: synced v{old_v} → v{shared.version}")

        return "# Sync Complete\n\n" + "\n".join(results)


def get_shared_status(ai_path: Path) -> str:
    """Get shared cognition status."""
    shared_storage = get_shared_storage(ai_path)
    stats = shared_storage.get_stats()
    agent_id = get_agent_id()

    lines = ["# Shared Cognition Status", ""]
    lines.append(f"**Agent ID**: {agent_id}")
    lines.append("")

    lines.append("## Published (my shared threads)")
    lines.append(f"- Count: {stats['published_count']}")

    published = shared_storage.get_all_published()
    if published:
        for p in published[:5]:
            lines.append(f"  - `{p.id}`: {p.title[:40]} (v{p.version}, {len(p.subscribers)} subs)")
    lines.append("")

    lines.append("## Subscriptions")
    lines.append(f"- Active: {stats['active_subscriptions']}")
    lines.append(f"- Total: {stats['subscriptions_count']}")

    subs = shared_storage.get_active_subscriptions()
    if subs:
        for s in subs[:5]:
            lines.append(f"  - `{s.shared_thread_id}`: {s.cached_title[:40]} (v{s.synced_version})")
    lines.append("")

    lines.append("## Cross-Agent Bridges")
    lines.append(f"- Active: {stats['active_bridges']}")
    lines.append(f"- Total: {stats['bridges_count']}")
    lines.append(f"- Pending outgoing: {stats['pending_outgoing']}")
    lines.append(f"- Pending incoming: {stats['pending_incoming']}")

    return "\n".join(lines)


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
