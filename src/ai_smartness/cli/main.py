#!/usr/bin/env python3
"""
AI Smartness CLI - Main entry point.

Usage:
    ai status              Show memory status
    ai threads             List threads (--prune, --show-weight)
    ai thread <id>         Show thread details
    ai bridges             List bridges (--prune, --show-weight)
    ai search <query>      Search threads
    ai reindex             Recalculate all embeddings
    ai health              System health check
    ai daemon [status|start|stop]  Manage daemon
    ai mode [status|light|normal|heavy|max]  View/change mode
    ai help                Show help message
"""

import argparse
import sys
from pathlib import Path


def find_ai_path() -> Path:
    """Find the .ai directory by searching upward from cwd."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        # Check for ai_smartness/.ai (underscore prefix folder)
        candidate = parent / "ai_smartness" / ".ai"
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
        description="AI Smartness - Memory visualization and management"
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
    threads_parser.add_argument(
        "--show-weight", "-w",
        action="store_true",
        help="Show weight column"
    )
    threads_parser.add_argument(
        "--prune",
        action="store_true",
        help="Apply decay and suspend low-weight threads"
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
    bridges_parser.add_argument(
        "--show-weight", "-w",
        action="store_true",
        help="Show weight column (decay status)"
    )
    bridges_parser.add_argument(
        "--prune",
        action="store_true",
        help="Apply decay and remove dead bridges"
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

    # reindex command
    reindex_parser = subparsers.add_parser("reindex", help="Recalculate all embeddings")
    reindex_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed progress"
    )
    reindex_parser.add_argument(
        "--reset-weights",
        action="store_true",
        help="Reset all thread weights to 1.0"
    )

    # health command
    health_parser = subparsers.add_parser("health", help="System health check")

    # daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Manage daemon")
    daemon_parser.add_argument(
        "action",
        nargs="?",
        choices=["status", "start", "stop"],
        default="status",
        help="Action to perform (default: status)"
    )

    # mode command
    mode_parser = subparsers.add_parser("mode", help="View or change operating mode")
    mode_parser.add_argument(
        "action",
        nargs="?",
        choices=["status", "light", "normal", "heavy", "max"],
        default="status",
        help="Mode to set or 'status' to view current (default: status)"
    )

    # help command (alias for --help)
    help_parser = subparsers.add_parser("help", help="Show this help message")

    args = parser.parse_args()

    if not args.command or args.command == "help":
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
        # Try relative imports first (when running as module)
        try:
            if args.command == "status":
                from .commands.status import run_status
                return run_status(ai_path)
            elif args.command == "threads":
                from .commands.threads import run_threads, run_threads_prune
                if args.prune:
                    return run_threads_prune(ai_path)
                return run_threads(ai_path, args.status, args.limit, args.show_weight)
            elif args.command == "thread":
                from .commands.threads import run_thread_detail
                return run_thread_detail(ai_path, args.id)
            elif args.command == "bridges":
                from .commands.bridges import run_bridges, run_prune
                if args.prune:
                    return run_prune(ai_path)
                return run_bridges(ai_path, args.thread, args.limit, args.show_weight)
            elif args.command == "search":
                from .commands.search import run_search
                return run_search(ai_path, args.query, args.limit)
            elif args.command == "reindex":
                from .commands.reindex import run_reindex
                return run_reindex(ai_path, args.verbose, args.reset_weights)
            elif args.command == "health":
                from .commands.health import run_health
                return run_health(ai_path)
            elif args.command == "daemon":
                from .commands.daemon import run_daemon_status, run_daemon_start, run_daemon_stop
                if args.action == "start":
                    return run_daemon_start(ai_path)
                elif args.action == "stop":
                    return run_daemon_stop(ai_path)
                else:
                    return run_daemon_status(ai_path)
            elif args.command == "mode":
                from .commands.mode import run_mode_status, run_mode_set
                if args.action == "status":
                    return run_mode_status(ai_path)
                else:
                    return run_mode_set(ai_path, args.action)
        except ImportError:
            # Fallback to absolute imports (when running as script)
            cli_dir = Path(__file__).parent
            sys.path.insert(0, str(cli_dir))

            if args.command == "status":
                from commands.status import run_status
                return run_status(ai_path)
            elif args.command == "threads":
                from commands.threads import run_threads, run_threads_prune
                if args.prune:
                    return run_threads_prune(ai_path)
                return run_threads(ai_path, args.status, args.limit, args.show_weight)
            elif args.command == "thread":
                from commands.threads import run_thread_detail
                return run_thread_detail(ai_path, args.id)
            elif args.command == "bridges":
                from commands.bridges import run_bridges, run_prune
                if args.prune:
                    return run_prune(ai_path)
                return run_bridges(ai_path, args.thread, args.limit, args.show_weight)
            elif args.command == "search":
                from commands.search import run_search
                return run_search(ai_path, args.query, args.limit)
            elif args.command == "reindex":
                from commands.reindex import run_reindex
                return run_reindex(ai_path, args.verbose, args.reset_weights)
            elif args.command == "health":
                from commands.health import run_health
                return run_health(ai_path)
            elif args.command == "daemon":
                from commands.daemon import run_daemon_status, run_daemon_start, run_daemon_stop
                if args.action == "start":
                    return run_daemon_start(ai_path)
                elif args.action == "stop":
                    return run_daemon_stop(ai_path)
                else:
                    return run_daemon_status(ai_path)
            elif args.command == "mode":
                from commands.mode import run_mode_status, run_mode_set
                if args.action == "status":
                    return run_mode_status(ai_path)
                else:
                    return run_mode_set(ai_path, args.action)

    except ImportError as e:
        print(f"Error loading command module: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
