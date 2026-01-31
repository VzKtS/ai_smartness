"""
Daemon management command.

Usage:
    ai daemon status    - Show daemon status
    ai daemon start     - Start daemon
    ai daemon stop      - Stop daemon
"""

import os
import time
from pathlib import Path
from typing import Optional


def is_process_running(pid: int) -> bool:
    """Check if a process is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_daemon_info(ai_path: Path) -> dict:
    """Get daemon status information."""
    pid_file = ai_path / "processor.pid"
    socket_path = ai_path / "processor.sock"
    log_file = ai_path / "processor.log"

    info = {
        "pid": None,
        "running": False,
        "socket_exists": socket_path.exists(),
        "log_file": str(log_file) if log_file.exists() else None
    }

    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            info["pid"] = pid
            info["running"] = is_process_running(pid)
        except (ValueError, OSError):
            pass

    return info


def run_daemon_status(ai_path: Path) -> int:
    """Show daemon status."""
    info = get_daemon_info(ai_path)

    print("=== Daemon Status ===")
    print(f"Project: {ai_path.parent}")
    print()

    if info["running"]:
        print(f"Status: Running (PID {info['pid']})")
        print(f"Socket: {ai_path / 'processor.sock'}")
    elif info["pid"]:
        print(f"Status: Stopped (stale PID {info['pid']})")
    else:
        print("Status: Stopped")

    if info["log_file"]:
        print(f"Log: {info['log_file']}")

    return 0


def run_daemon_start(ai_path: Path) -> int:
    """Start the daemon."""
    info = get_daemon_info(ai_path)

    if info["running"]:
        print(f"Daemon already running (PID {info['pid']})")
        return 0

    # Import client to start daemon
    try:
        import sys
        package_dir = ai_path.parent
        if str(package_dir.parent) not in sys.path:
            sys.path.insert(0, str(package_dir.parent))

        package_name = package_dir.name
        import importlib
        client_mod = importlib.import_module(f"{package_name}.daemon.client")
        ensure_daemon_running = client_mod.ensure_daemon_running

        print("Starting daemon...")
        if ensure_daemon_running(ai_path, max_wait=5.0):
            # Get new PID
            time.sleep(0.5)
            new_info = get_daemon_info(ai_path)
            if new_info["running"]:
                print(f"Daemon started (PID {new_info['pid']})")
                return 0
            else:
                print("Warning: Daemon may not have started properly")
                print(f"Check log: {ai_path / 'processor.log'}")
                return 1
        else:
            print("Failed to start daemon")
            print(f"Check logs: {ai_path / 'daemon_stderr.log'}")
            return 1

    except Exception as e:
        print(f"Error starting daemon: {e}")
        return 1


def run_daemon_stop(ai_path: Path) -> int:
    """Stop the daemon."""
    info = get_daemon_info(ai_path)

    if not info["running"]:
        print("Daemon is not running")
        # Clean up stale files
        pid_file = ai_path / "processor.pid"
        socket_path = ai_path / "processor.sock"
        if pid_file.exists():
            pid_file.unlink()
        if socket_path.exists():
            socket_path.unlink()
        return 0

    pid = info["pid"]
    print(f"Stopping daemon (PID {pid})...")

    try:
        # Try graceful shutdown first via socket
        socket_path = ai_path / "processor.sock"
        if socket_path.exists():
            try:
                import socket
                import json
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect(str(socket_path))
                sock.sendall(json.dumps({"shutdown": True}).encode('utf-8') + b'\n')
                sock.close()
                time.sleep(1.0)
            except Exception:
                pass

        # Check if stopped
        if not is_process_running(pid):
            print("Daemon stopped gracefully")
            # Clean up files
            (ai_path / "processor.pid").unlink(missing_ok=True)
            (ai_path / "processor.sock").unlink(missing_ok=True)
            return 0

        # SIGTERM
        os.kill(pid, 15)
        time.sleep(1.0)

        if not is_process_running(pid):
            print("Daemon stopped (SIGTERM)")
            (ai_path / "processor.pid").unlink(missing_ok=True)
            (ai_path / "processor.sock").unlink(missing_ok=True)
            return 0

        # SIGKILL
        os.kill(pid, 9)
        time.sleep(0.5)

        if not is_process_running(pid):
            print("Daemon killed (SIGKILL)")
            (ai_path / "processor.pid").unlink(missing_ok=True)
            (ai_path / "processor.sock").unlink(missing_ok=True)
            return 0

        print(f"Failed to stop daemon (PID {pid})")
        return 1

    except OSError as e:
        print(f"Error stopping daemon: {e}")
        return 1
