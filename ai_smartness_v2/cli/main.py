#!/usr/bin/env python3
"""
AI Smartness v2 CLI - Main entry point.

Usage:
    ai status              Show memory status
    ai threads             List threads
    ai thread <id>         Show thread details
    ai bridges             List bridges
    ai search <query>      Search threads
"""

import argparse
import sys
from pathlib import Path


def find_ai_path() -> Path:
    """Find the .ai directory by searching upward from cwd."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        # Check for _ai_smartness_v2/.ai (underscore prefix folder)
        candidate = parent / "_ai_smartness_v2" / ".ai"
        if candidate.exists():
            return candidate
        # Check for .ai directly
        candidate = parent / ".ai"
        if candidate.exists():
            return candidate
    return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ai",
        description="AI Smartness v2 - Memory visualization and management"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status command
    status_parser = subparsers.add_parser("status", help="Show memory status")

    # threads command
    threads_parser = subparsers.add_parser("threads", help="List threads")
    threads_parser.add_argument(
        "--status", "-s",
        choices=["active", "suspended", "archived", "all"],
        default="active",
        help="Filter by status (default: active)"
    )
    threads_parser.add_argument(
        "--limit", "-n",
        type=int,
        default=10,
        help="Number of threads to show (default: 10)"
    )

    # thread command (single thread detail)
    thread_parser = subparsers.add_parser("thread", help="Show thread details")
    thread_parser.add_argument("id", help="Thread ID (or prefix)")

    # bridges command
    bridges_parser = subparsers.add_parser("bridges", help="List bridges")
    bridges_parser.add_argument(
        "--thread", "-t",
        help="Filter bridges by thread ID"
    )
    bridges_parser.add_argument(
        "--limit", "-n",
        type=int,
        default=20,
        help="Number of bridges to show (default: 20)"
    )

    # search command
    search_parser = subparsers.add_parser("search", help="Search threads")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--limit", "-n",
        type=int,
        default=5,
        help="Number of results (default: 5)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Find .ai directory
    ai_path = find_ai_path()
    if not ai_path:
        print("Error: Could not find .ai directory")
        print("Make sure you're in a project with AI Smartness installed")
        return 1

    # Import and run commands
    try:
        if args.command == "status":
            from .commands.status import run_status
            return run_status(ai_path)

        elif args.command == "threads":
            from .commands.threads import run_threads
            return run_threads(ai_path, args.status, args.limit)

        elif args.command == "thread":
            from .commands.threads import run_thread_detail
            return run_thread_detail(ai_path, args.id)

        elif args.command == "bridges":
            from .commands.bridges import run_bridges
            return run_bridges(ai_path, args.thread, args.limit)

        elif args.command == "search":
            from .commands.search import run_search
            return run_search(ai_path, args.query, args.limit)

    except ImportError as e:
        print(f"Error loading command module: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
