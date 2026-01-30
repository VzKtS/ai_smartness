"""
Daemon module for AI Smartness v2.

Provides a persistent background processor for thread management.
Uses Unix socket for fast, lightweight communication from hooks.
"""

from .client import send_capture, ensure_daemon_running, is_daemon_running

__all__ = [
    "send_capture",
    "ensure_daemon_running",
    "is_daemon_running"
]
