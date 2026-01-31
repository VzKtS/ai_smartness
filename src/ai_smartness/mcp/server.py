#!/usr/bin/env python3
"""
AI Smartness MCP Server

A local MCP server that exposes AI Smartness memory tools to Claude Code agents.
Runs as a subprocess communicating via stdio (JSON-RPC).

Tools:
- ai_recall: Semantic memory search
- ai_merge: Merge two threads
- ai_split: Split a drifted thread
- ai_unlock: Unlock a split-locked thread
- ai_help: Documentation
- ai_status: Memory status

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
        bridge_count = bridge_storage.count()

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
