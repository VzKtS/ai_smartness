"""Hooks for Claude Code integration.

Available hooks:
- capture.py: PostToolUse hook for capturing tool results
- inject.py: UserPromptSubmit hook for context injection
- compact.py: PreCompact hook for synthesis generation
"""

# Hooks are standalone scripts, not imported as modules
# They are executed directly by Claude Code hooks system

__all__ = []
