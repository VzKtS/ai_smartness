"""
Daemon Client - Lightweight client for communicating with processor daemon.

This module provides fast, non-blocking communication with the processor daemon.
Designed to be imported by hooks for minimal overhead.
"""

import os
import socket
import json
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any


def send_capture(
    socket_path: Path,
    data: Dict[str, Any],
    timeout: float = 0.5,
    wait_response: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Send a capture request to the daemon.

    Args:
        socket_path: Path to the Unix socket
        data: Data to send (dict will be JSON encoded)
        timeout: Connection timeout in seconds
        wait_response: Whether to wait for response

    Returns:
        Response dict if wait_response=True, None otherwise
    """
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(str(socket_path))

        # Send data
        sock.sendall(json.dumps(data).encode('utf-8') + b'\n')

        if wait_response:
            # Wait for response
            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                if b'\n' in response_data:
                    break

            sock.close()

            if response_data:
                return json.loads(response_data.decode('utf-8').strip())
            return None
        else:
            sock.close()
            return {"status": "sent"}

    except socket.timeout:
        return None
    except ConnectionRefusedError:
        return None
    except FileNotFoundError:
        return None
    except Exception:
        return None


def is_daemon_running(ai_path: Path) -> bool:
    """
    Check if the daemon is running.

    Args:
        ai_path: Path to .ai directory

    Returns:
        True if daemon is running and responding
    """
    socket_path = ai_path / "processor.sock"

    if not socket_path.exists():
        return False

    # Try to ping
    response = send_capture(socket_path, {"ping": True}, wait_response=True)
    return response is not None and response.get("pong") is True


def get_daemon_status(ai_path: Path) -> Optional[Dict[str, Any]]:
    """
    Get daemon status.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Status dict or None if not running
    """
    socket_path = ai_path / "processor.sock"

    if not socket_path.exists():
        return None

    return send_capture(socket_path, {"status": True}, wait_response=True)


def stop_daemon(ai_path: Path) -> bool:
    """
    Stop the daemon gracefully.

    Args:
        ai_path: Path to .ai directory

    Returns:
        True if shutdown initiated
    """
    socket_path = ai_path / "processor.sock"

    if not socket_path.exists():
        return False

    response = send_capture(socket_path, {"shutdown": True}, wait_response=True)
    return response is not None


def ensure_daemon_running(ai_path: Path, max_wait: float = 2.0) -> bool:
    """
    Ensure the daemon is running, starting it if necessary.

    Args:
        ai_path: Path to .ai directory
        max_wait: Maximum time to wait for daemon startup

    Returns:
        True if daemon is running
    """
    socket_path = ai_path / "processor.sock"
    db_path = ai_path / "db"

    # Check if already running
    if is_daemon_running(ai_path):
        return True

    # Clean up stale socket
    if socket_path.exists():
        try:
            socket_path.unlink()
        except Exception:
            pass

    # Clean up stale PID file
    pid_file = ai_path / "processor.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)
        except (ValueError, OSError):
            # Process doesn't exist, remove stale PID
            try:
                pid_file.unlink()
            except Exception:
                pass

    # Start the daemon
    try:
        # Find the processor script path
        # Use direct path since folder may be hidden (ai_smartness_v2)
        package_dir = Path(__file__).parent.parent
        processor_path = package_dir / "daemon" / "processor.py"

        # Try to start daemon
        env = os.environ.copy()
        env["PYTHONPATH"] = str(package_dir.parent) + ":" + env.get("PYTHONPATH", "")

        subprocess.Popen(
            [
                "python3", str(processor_path),
                "--db-path", str(db_path)
            ],
            env=env,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    except Exception:
        return False

    # Wait for daemon to be ready
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if is_daemon_running(ai_path):
            return True
        time.sleep(0.1)

    return False


def send_capture_with_retry(
    ai_path: Path,
    data: Dict[str, Any],
    max_retries: int = 2
) -> bool:
    """
    Send capture with automatic daemon startup and retry.

    Args:
        ai_path: Path to .ai directory
        data: Capture data
        max_retries: Maximum retry attempts

    Returns:
        True if sent successfully
    """
    socket_path = ai_path / "processor.sock"

    for attempt in range(max_retries + 1):
        # Try to send
        result = send_capture(socket_path, data)
        if result is not None:
            return True

        # Daemon not running, try to start
        if attempt < max_retries:
            if ensure_daemon_running(ai_path):
                continue

    return False
