#!/usr/bin/env python3
"""
Processor Daemon - Background thread processing for AI Smartness v2.

This daemon:
1. Loads heavy modules once at startup
2. Listens on a Unix socket for capture requests
3. Processes captures through ThreadManager and GossipPropagator
4. Runs persistently in background

Usage:
    python3 ai_smartness_v2/daemon/processor.py --db-path /path/to/.ai/db

Or via client (internal):
    from daemon.client import ensure_daemon_running
    ensure_daemon_running(ai_path)
"""

import os
import sys
import json
import socket
import signal
import argparse
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ProcessorDaemon:
    """
    Background daemon for processing thread captures.

    Loads StorageManager, ThreadManager, and GossipPropagator once
    and processes incoming requests via Unix socket.
    """

    # Tool to source_type mapping
    # Must match keys in EXTRACTION_PROMPTS (extractor.py)
    SOURCE_MAP = {
        # File operations (match extractor.py keys)
        "Read": "read",
        "Write": "write",
        "Edit": "write",
        "NotebookEdit": "write",
        # Search operations (use "read" - examining file content)
        "Glob": "read",
        "Grep": "read",
        # External operations
        "Task": "task",
        "WebFetch": "fetch",
        "WebSearch": "fetch",
        "Bash": "command",
        # User prompts (via inject.py)
        "UserPrompt": "prompt",
    }

    def __init__(self, db_path: Path):
        """
        Initialize the daemon.

        Args:
            db_path: Path to the database directory (.ai/db)
        """
        self.db_path = Path(db_path)
        self.ai_path = self.db_path.parent  # .ai directory
        self.socket_path = self.ai_path / "processor.sock"
        self.pid_file = self.ai_path / "processor.pid"
        self.log_file = self.ai_path / "processor.log"

        self.running = False
        self.server_socket: Optional[socket.socket] = None

        # Heavy modules - loaded once
        self.storage = None
        self.thread_manager = None
        self.gossip = None

    def _init_modules(self):
        """Initialize the heavy modules."""
        logger.info("Loading modules...")

        try:
            # Add package parent to sys.path so we can import as a package
            # ai_smartness_v2/ is in /project/ai_smartness_v2/
            # We need to add /project/ to sys.path
            package_dir = Path(__file__).parent.parent  # ai_smartness_v2/
            package_parent = package_dir.parent  # /project/
            package_name = package_dir.name  # "ai_smartness_v2"

            if str(package_parent) not in sys.path:
                sys.path.insert(0, str(package_parent))

            # Now we can import using absolute package paths
            # Import dynamically to avoid issues at module load time
            import importlib
            storage_mod = importlib.import_module(f"{package_name}.storage.manager")
            thread_manager_mod = importlib.import_module(f"{package_name}.intelligence.thread_manager")
            gossip_mod = importlib.import_module(f"{package_name}.intelligence.gossip")

            StorageManager = storage_mod.StorageManager
            ThreadManager = thread_manager_mod.ThreadManager
            GossipPropagator = gossip_mod.GossipPropagator

            # StorageManager expects root_path (parent of .ai)
            # db_path = /path/.ai/db → root_path = /path
            root_path = self.ai_path.parent
            self.storage = StorageManager(root_path)
            self.thread_manager = ThreadManager(self.storage)
            self.gossip = GossipPropagator(self.storage)

            logger.info("Modules loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load modules: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _setup_socket(self):
        """Create and bind the Unix socket."""
        # Remove existing socket file
        if self.socket_path.exists():
            self.socket_path.unlink()

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(str(self.socket_path))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)  # Allow checking self.running

        # Set permissions
        os.chmod(str(self.socket_path), 0o600)

        logger.info(f"Socket listening on {self.socket_path}")

    def _write_pid(self):
        """Write PID file."""
        self.pid_file.write_text(str(os.getpid()))
        logger.info(f"PID {os.getpid()} written to {self.pid_file}")

    def _cleanup(self):
        """Cleanup resources on shutdown."""
        logger.info("Cleaning up...")

        if self.server_socket:
            self.server_socket.close()

        if self.socket_path.exists():
            self.socket_path.unlink()

        if self.pid_file.exists():
            self.pid_file.unlink()

        logger.info("Cleanup complete")

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def _handle_client(self, client_socket: socket.socket):
        """Handle a client connection."""
        try:
            # Read data (expect JSON line)
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n' in data:
                    break

            if not data:
                return

            # Parse JSON
            try:
                request = json.loads(data.decode('utf-8').strip())
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON: {e}")
                self._send_response(client_socket, {"error": "Invalid JSON"})
                return

            # Handle request
            response = self._process_request(request)
            self._send_response(client_socket, response)

        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def _send_response(self, client_socket: socket.socket, response: dict):
        """Send response to client."""
        try:
            client_socket.sendall(json.dumps(response).encode('utf-8') + b'\n')
        except Exception:
            pass

    def _process_request(self, request: dict) -> dict:
        """
        Process a capture request.

        Args:
            request: Request dictionary with tool, content, file_path

        Returns:
            Response dictionary
        """
        # Handle ping
        if request.get("ping"):
            return {"pong": True, "pid": os.getpid()}

        # Handle status
        if request.get("status"):
            return {
                "running": True,
                "pid": os.getpid(),
                "uptime": self._get_uptime(),
                "threads_count": len(self.storage.threads.get_all()) if self.storage else 0
            }

        # Handle shutdown
        if request.get("shutdown"):
            self.running = False
            return {"status": "shutting_down"}

        # Handle capture
        tool = request.get("tool", "")
        content = request.get("content", "")
        file_path = request.get("file_path")

        if not content:
            return {"status": "skipped", "reason": "empty_content"}

        try:
            result = self._process_capture(tool, content, file_path)
            return result
        except Exception as e:
            logger.error(f"Error processing capture: {e}")
            return {"status": "error", "error": str(e)}

    def _process_capture(self, tool: str, content: str, file_path: Optional[str]) -> dict:
        """
        Process a capture through ThreadManager.

        Args:
            tool: Tool name (Read, Write, Task, etc.)
            content: Content to process
            file_path: Optional file path

        Returns:
            Result dictionary
        """
        if not self.thread_manager:
            return {"status": "error", "error": "ThreadManager not initialized"}

        # Map tool to source type
        source_type = self.SOURCE_MAP.get(tool, "prompt")

        # Process through ThreadManager
        thread, extraction = self.thread_manager.process_input(
            content=content,
            source_type=source_type,
            file_path=file_path
        )

        # Trigger gossip propagation
        if self.gossip:
            self.gossip.on_thread_modified(thread)

        logger.info(f"Processed [{tool}] → Thread {thread.id[:8]}... '{thread.title[:30]}'")

        return {
            "status": "ok",
            "thread_id": thread.id,
            "thread_title": thread.title,
            "action": "created" if len(thread.messages) == 1 else "continued"
        }

    def _get_uptime(self) -> str:
        """Get daemon uptime."""
        if hasattr(self, '_start_time'):
            delta = datetime.now() - self._start_time
            return str(delta).split('.')[0]
        return "unknown"

    def run(self):
        """Run the daemon main loop."""
        # Initialize modules
        if not self._init_modules():
            logger.error("Failed to initialize, exiting")
            return 1

        # Setup socket
        self._setup_socket()

        # Write PID
        self._write_pid()

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        self.running = True
        self._start_time = datetime.now()

        logger.info("Daemon started, waiting for connections...")

        while self.running:
            try:
                client_socket, _ = self.server_socket.accept()
                # Handle in thread for non-blocking
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                )
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Accept error: {e}")

        self._cleanup()
        logger.info("Daemon stopped")
        return 0

    def daemonize(self):
        """Fork into background daemon."""
        # First fork
        pid = os.fork()
        if pid > 0:
            # Parent exits
            sys.exit(0)

        # Create new session
        os.setsid()

        # Second fork
        pid = os.fork()
        if pid > 0:
            sys.exit(0)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        # Redirect to log file
        log_fd = open(self.log_file, 'a')
        os.dup2(log_fd.fileno(), sys.stdout.fileno())
        os.dup2(log_fd.fileno(), sys.stderr.fileno())

        # Run main loop
        return self.run()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI Smartness v2 Processor Daemon")
    parser.add_argument(
        "--db-path",
        required=True,
        help="Path to database directory (.ai/db)"
    )
    parser.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="Run in foreground (don't daemonize)"
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        db_path.mkdir(parents=True, exist_ok=True)

    daemon = ProcessorDaemon(db_path)

    if args.foreground:
        sys.exit(daemon.run())
    else:
        sys.exit(daemon.daemonize())


if __name__ == "__main__":
    main()
