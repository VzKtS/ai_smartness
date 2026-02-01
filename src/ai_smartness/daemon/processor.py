#!/usr/bin/env python3
"""
Processor Daemon - Background thread processing for AI Smartness.

This daemon:
1. Loads heavy modules once at startup
2. Listens on a Unix socket for capture requests
3. Processes captures through ThreadManager and GossipPropagator
4. Runs persistently in background

Usage:
    python3 ai_smartness/daemon/processor.py --db-path /path/to/.ai/db

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

        # Pending context for coherence-based child linking
        # Set after every thread creation, checked before next capture
        # Creates natural parent-child chains based on semantic coherence
        self.pending_context: Optional[Dict[str, Any]] = None
        self.pending_context_lock = threading.Lock()

        # Periodic pruning (every 5 minutes)
        self.PRUNE_INTERVAL_SECONDS = 300  # 5 minutes
        self.last_prune_time: Optional[datetime] = None

    def _init_modules(self):
        """Initialize the heavy modules."""
        logger.info("Loading modules...")

        try:
            # Add package parent to sys.path so we can import as a package
            # ai_smartness/ is in /project/ai_smartness/
            # We need to add /project/ to sys.path
            package_dir = Path(__file__).parent.parent  # ai_smartness/
            package_parent = package_dir.parent  # /project/
            package_name = package_dir.name  # "ai_smartness"

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

        Universal coherence-based child linking:
        - Every tool creates thread + sets pending_context
        - Next capture checks coherence with pending_context
        - High coherence (>0.6) → child thread
        - Medium coherence (0.3-0.6) → orphan thread (new root)
        - Low coherence (<0.3) → forget (skip capture)

        This creates a natural chain of parent-child threads where
        the coherence score determines the relationship strength.

        Args:
            tool: Tool name (Read, Write, Task, etc.)
            content: Content to process
            file_path: Optional file path

        Returns:
            Result dictionary
        """
        if not self.thread_manager:
            return {"status": "error", "error": "ThreadManager not initialized"}

        # Clean content before processing
        logger.info(f"Processing [{tool}]: {len(content)} chars input")

        try:
            # Import cleaner dynamically using absolute file path
            import importlib.util
            cleaner_path = Path(__file__).parent.parent / "processing" / "cleaner.py"

            spec = importlib.util.spec_from_file_location("cleaner", cleaner_path)
            cleaner_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cleaner_module)

            cleaned_content, extracted_path = cleaner_module.clean_tool_output(content, tool)
        except Exception as e:
            logger.error(f"Cleaner error [{tool}]: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback: use raw content
            cleaned_content = content[:5000] if len(content) > 5000 else content
            extracted_path = None

        # Log cleaning stats
        logger.info(f"Cleaned [{tool}]: {len(content)} → {len(cleaned_content)} chars")

        # Use extracted path if none provided
        if not file_path and extracted_path:
            file_path = extracted_path

        # Skip if cleaning resulted in empty content
        if not cleaned_content:
            logger.warning(f"Skipped [{tool}]: empty after cleaning (input was {len(content)} chars)")
            return {"status": "skipped", "reason": "empty_after_cleaning"}

        # Map tool to source type
        source_type = self.SOURCE_MAP.get(tool, "prompt")

        # Check for pending context (coherence-based child linking)
        # Every capture checks coherence with the previous one
        parent_thread_id = None
        with self.pending_context_lock:
            if self.pending_context:
                # Check coherence with pending context
                parent_thread_id = self._check_coherence_and_decide(cleaned_content)

        # Handle "forget" case - low coherence, skip thread creation
        if parent_thread_id == "__FORGET__":
            logger.info(f"Skipped [{tool}]: low coherence with context (forget)")
            return {"status": "skipped", "reason": "low_coherence_forget"}

        # Process through ThreadManager
        thread, extraction = self.thread_manager.process_input(
            content=cleaned_content,
            source_type=source_type,
            file_path=file_path,
            parent_hint=parent_thread_id  # Pass parent hint for child linking
        )

        # Set pending_context for next capture (universal coherence chain)
        with self.pending_context_lock:
            self.pending_context = {
                "thread_id": thread.id,
                "content": cleaned_content,
                "tool": tool,
                "timestamp": datetime.now()
            }
            logger.info(f"Set pending_context from [{tool}] → {thread.id[:8]}...")

        # Trigger gossip propagation
        if self.gossip:
            self.gossip.on_thread_modified(thread)

        # Update heartbeat with hot thread (v4.2)
        self._update_heartbeat_thread(thread.id, thread.title)

        logger.info(f"Processed [{tool}] → Thread {thread.id[:8]}... '{thread.title[:30]}'")

        return {
            "status": "ok",
            "thread_id": thread.id,
            "thread_title": thread.title,
            "action": "created" if len(thread.messages) == 1 else "continued",
            "parent_id": parent_thread_id
        }

    def _check_coherence_and_decide(self, content: str) -> Optional[str]:
        """
        Check coherence with pending context and decide action.

        Returns:
            parent_thread_id if child, None if orphan/forget
        """
        if not self.pending_context:
            return None

        context_content = self.pending_context.get("content", "")
        context_thread_id = self.pending_context.get("thread_id")
        context_tool = self.pending_context.get("tool", "")

        # Check context age (expire after 10 minutes)
        context_time = self.pending_context.get("timestamp")
        if context_time:
            age_minutes = (datetime.now() - context_time).total_seconds() / 60
            if age_minutes > 10:
                logger.info(f"Pending context expired ({age_minutes:.1f} min old)")
                self.pending_context = None
                return None

        try:
            # Import coherence module dynamically
            import importlib.util
            coherence_path = Path(__file__).parent.parent / "processing" / "coherence.py"

            spec = importlib.util.spec_from_file_location("coherence", coherence_path)
            coherence_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(coherence_module)

            # Check coherence
            coherence_score, reason = coherence_module.check_coherence(
                context_content,
                content
            )

            # Decide action
            action = coherence_module.decide_thread_action(coherence_score)

            logger.info(f"Coherence with [{context_tool}]: {coherence_score:.2f} → {action} ({reason})")

            if action == "child":
                # Clear context - new thread will set its own
                self.pending_context = None
                return context_thread_id
            elif action == "forget":
                # KEEP pending_context - next tool should try with same context
                # This preserves the chain even when we skip noise
                return "__FORGET__"
            else:  # orphan
                # Clear context - new root thread will set its own
                self.pending_context = None
                return None

        except Exception as e:
            logger.error(f"Coherence check error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Clear context on error, default to orphan
            self.pending_context = None
            return None

    def _get_uptime(self) -> str:
        """Get daemon uptime."""
        if hasattr(self, '_start_time'):
            delta = datetime.now() - self._start_time
            return str(delta).split('.')[0]
        return "unknown"

    def _prune_timer_loop(self):
        """
        Background thread that runs periodic pruning and heartbeat.

        Applies decay to threads and bridges, suspending/deleting
        those below thresholds. Also increments heartbeat counter.
        V5.1: Also checks for session idle and updates session state.
        Runs every PRUNE_INTERVAL_SECONDS (default 5 min).
        """
        import time
        logger.info(f"Prune timer started (interval: {self.PRUNE_INTERVAL_SECONDS}s)")

        while self.running:
            time.sleep(self.PRUNE_INTERVAL_SECONDS)

            if not self.running:
                break

            try:
                # Increment heartbeat (v4.1)
                beat = self._increment_heartbeat()
                if beat is not None:
                    logger.info(f"Heartbeat: {beat}")

                # V5.1: Check for session idle
                self._check_session_idle()

                logger.info("Running periodic prune...")

                # Prune threads (suspend low-weight)
                if self.thread_manager:
                    result = self.thread_manager.prune_threads()
                    if result.get("suspended_count", 0) > 0:
                        logger.info(f"Pruned threads: {result['suspended_count']} suspended")

                # Prune bridges (delete dead)
                if self.gossip:
                    pruned = self.gossip.prune_dead_bridges()
                    if pruned > 0:
                        logger.info(f"Pruned bridges: {pruned} deleted")

                self.last_prune_time = datetime.now()

            except Exception as e:
                logger.error(f"Prune error: {e}")

        logger.info("Prune timer stopped")

    def _increment_heartbeat(self) -> Optional[int]:
        """
        Increment heartbeat counter (v4.1).

        Returns:
            New beat count, or None on error
        """
        try:
            import importlib.util
            heartbeat_path = Path(__file__).parent.parent / "storage" / "heartbeat.py"

            if not heartbeat_path.exists():
                return None

            spec = importlib.util.spec_from_file_location("heartbeat", heartbeat_path)
            heartbeat_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(heartbeat_module)

            return heartbeat_module.increment_beat(self.ai_path)

        except Exception as e:
            logger.debug(f"Heartbeat error: {e}")
            return None

    def _update_heartbeat_thread(self, thread_id: str, thread_title: str) -> None:
        """
        Update heartbeat with current hot thread (v4.2).

        Args:
            thread_id: Current thread ID
            thread_title: Current thread title
        """
        try:
            import importlib.util
            heartbeat_path = Path(__file__).parent.parent / "storage" / "heartbeat.py"

            if not heartbeat_path.exists():
                return

            spec = importlib.util.spec_from_file_location("heartbeat", heartbeat_path)
            heartbeat_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(heartbeat_module)

            heartbeat = heartbeat_module.load_heartbeat(self.ai_path)
            heartbeat["last_thread_id"] = thread_id
            heartbeat["last_thread_title"] = thread_title
            heartbeat_module.save_heartbeat(self.ai_path, heartbeat)

            logger.debug(f"Heartbeat thread updated: {thread_id[:8]}...")

        except Exception as e:
            logger.debug(f"Heartbeat thread update error: {e}")

    def _check_session_idle(self) -> None:
        """
        V5.1: Check if session is idle and update session state.

        Marks session as idle if no activity for > 5 minutes.
        This enables better context injection on session resume.
        """
        try:
            # Import session module
            package_dir = Path(__file__).parent.parent
            package_parent = package_dir.parent
            package_name = package_dir.name

            if str(package_parent) not in sys.path:
                sys.path.insert(0, str(package_parent))

            import importlib
            session_mod = importlib.import_module(f"{package_name}.models.session")

            state = session_mod.load_session_state(self.ai_path)

            # Check if session should be marked idle
            minutes_since = state.get_minutes_since_activity()

            if minutes_since > 5 and state.status == "active":
                state.mark_idle()
                session_mod.save_session_state(self.ai_path, state)
                logger.info(f"Session marked idle (inactive for {int(minutes_since)} min)")

        except Exception as e:
            logger.debug(f"Session idle check error: {e}")

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

        # Start prune timer thread
        prune_thread = threading.Thread(
            target=self._prune_timer_loop,
            daemon=True,
            name="prune-timer"
        )
        prune_thread.start()

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
    parser = argparse.ArgumentParser(description="AI Smartness Processor Daemon")
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
