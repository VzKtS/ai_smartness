"""Health command - Display system health metrics."""

import json
import os
from pathlib import Path


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def run_health(ai_path: Path) -> int:
    """
    Display system health metrics.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Exit code
    """
    threads_dir = ai_path / "db" / "threads"
    bridges_dir = ai_path / "db" / "bridges"

    # Load threads
    threads = []
    if threads_dir.exists():
        for f in threads_dir.glob("thread_*.json"):
            try:
                threads.append(json.loads(f.read_text()))
            except Exception:
                pass

    # Load bridges
    bridges = []
    if bridges_dir.exists():
        for f in bridges_dir.glob("bridge_*.json"):
            try:
                bridges.append(json.loads(f.read_text()))
            except Exception:
                pass

    # Calculate metrics
    total_threads = len(threads)
    active = sum(1 for t in threads if t.get("status") == "active")
    suspended = sum(1 for t in threads if t.get("status") == "suspended")
    archived = sum(1 for t in threads if t.get("status") == "archived")

    # Continuation rate
    multi_msg = sum(1 for t in threads if len(t.get("messages", [])) > 1)
    continuation_rate = (multi_msg / total_threads * 100) if total_threads else 0

    # Embedding coverage
    with_embedding = sum(
        1 for t in threads
        if t.get("embedding") and any(x != 0 for x in t.get("embedding", []))
    )
    embedding_coverage = (with_embedding / total_threads * 100) if total_threads else 0

    # Daemon status
    pid_file = ai_path / "processor.pid"
    daemon_running = False
    daemon_pid = None
    if pid_file.exists():
        try:
            daemon_pid = int(pid_file.read_text().strip())
            daemon_running = is_process_running(daemon_pid)
        except Exception:
            pass

    # Display metrics
    print("=" * 40)
    print("AI Smartness v2 - Health Check")
    print("=" * 40)
    print()
    print(f"Threads: {total_threads}")
    print(f"  - Active:    {active}")
    print(f"  - Suspended: {suspended}")
    print(f"  - Archived:  {archived}")
    print()
    print(f"Bridges: {len(bridges)}")
    print()
    print(f"Continuation rate: {continuation_rate:.1f}%")
    print(f"  ({multi_msg}/{total_threads} threads with >1 message)")
    print()
    print(f"Embedding coverage: {embedding_coverage:.1f}%")
    print(f"  ({with_embedding}/{total_threads} threads with valid embeddings)")
    print()
    if daemon_running:
        print(f"Daemon: Running (PID {daemon_pid})")
    else:
        print("Daemon: Stopped")
    print()

    # Warnings
    warnings = []
    if continuation_rate < 10 and total_threads > 10:
        warnings.append("Low continuation rate - threads not consolidating")
    if embedding_coverage < 90 and total_threads > 5:
        warnings.append("Missing embeddings - run 'ai reindex'")
    if not daemon_running:
        warnings.append("Daemon not running - captures not being processed")

    if warnings:
        print("-" * 40)
        print("Warnings:")
        for w in warnings:
            print(f"  ! {w}")
        print()

    return 0
