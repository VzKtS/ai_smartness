# AI Smartness v3 - User Guide

## Quick Start

1. **Install** in your project:
   ```bash
   /path/to/ai_smartness-DEV/install.sh /path/to/your/project
   ```

2. **Work normally** - the system captures everything automatically

3. **Check status** anytime:
   ```bash
   ai status
   ```
   Or type `ai status` directly in your prompt! (v3.0.0)

That's it. The system is 100% transparent.

---

## Key Concepts

### Threads

A **Thread** is a semantic work unit representing a topic or task.

| Status | Description |
|--------|-------------|
| `active` | Currently being worked on |
| `suspended` | Paused, can be reactivated |
| `archived` | Completed or dormant |

Threads contain:
- **Title**: Auto-generated semantic title
- **Messages**: History of interactions
- **Summary**: Auto-generated summary
- **Topics**: Key concepts extracted
- **Embedding**: Vector for similarity search

### ThinkBridges

A **ThinkBridge** is a semantic connection between two threads.

| Type | Meaning |
|------|---------|
| `extends` | A extends/refines B |
| `depends` | A depends on B |
| `contradicts` | A and B are in tension |
| `replaces` | A replaces B |
| `child_of` | A is a subtopic of B |

Bridges are created automatically when the system detects semantic similarity.

### User Rules

The system detects and remembers your preferences. Say things like:
- "remember: always use TypeScript"
- "rule: no direct commits to main"
- "always make a plan before implementation"
- "never use console.log in production"

These rules are stored permanently and injected into every prompt.

---

## CLI in Prompt (v3.0.0)

Type CLI commands directly in your prompt and they will be executed automatically:

```
You: ai status
Claude: [Shows memory status from CLI]

You: ai threads
Claude: [Lists active threads]

You: ai search authentication
Claude: [Shows search results for "authentication"]
```

**Supported commands:** `ai status`, `ai threads`, `ai thread <id>`, `ai bridges`, `ai search <query>`, `ai health`, `ai daemon`, `ai mode`, `ai help`

This is equivalent to running the command in your terminal - the result is injected into Claude's context and summarized for you.

---

## CLI Reference

### `ai status`

Shows global overview:
```
=== AI Smartness Status ===
Project: MyProject

Threads: 45 total
  Active:    12
  Suspended: 33
  Archived:  0

Bridges: 234 connections

Last activity: 2026-01-29 15:30:22
Current thread: "Authentication System"
```

### `ai threads`

List threads with filtering:
```bash
ai threads                    # Active threads (default)
ai threads --status active    # Active only
ai threads --status suspended # Suspended only
ai threads --status all       # All threads
ai threads --limit 20         # Limit to 20 results
ai threads --prune            # Apply decay and suspend low-weight threads
```

Output:
```
ID         Title                           Status    Weight  Messages
---------- ------------------------------- --------- ------- --------
abc123...  Authentication System           active    0.92    8
def456...  Database Schema Design          active    0.78    5
ghi789...  API Rate Limiting               suspended 0.45    3
```

### `ai thread <id>`

Show thread details:
```bash
ai thread abc123
```

### `ai bridges`

List semantic connections:
```bash
ai bridges                    # All bridges
ai bridges --thread abc123    # Bridges for specific thread
ai bridges --limit 50         # Limit results
ai bridges --prune            # Apply decay and remove dead bridges
```

Output:
```
Source                Target                Type       Confidence
--------------------- --------------------- ---------- ----------
Authentication...     Database Schema...    depends    0.85
API Rate Limiting...  Authentication...     extends    0.72
```

### `ai search`

Semantic search across all threads:
```bash
ai search "authentication"
ai search "database migration" --limit 10
```

### `ai health`

System health check:
```bash
ai health
```

Output:
```
=== AI Smartness Health ===
Threads: 158 (100 active, 58 suspended)
Bridges: 3374
Continuation rate: 23.4%
Embedding coverage: 100.0%
Daemon: Running (PID 12345)
```

**Key metrics:**
- **Continuation rate**: % of threads with >1 message (higher is better)
- **Embedding coverage**: % of threads with valid embeddings (should be 100%)
- **Daemon**: Should be "Running"

### `ai reindex`

Recalculate all embeddings:
```bash
ai reindex           # Standard
ai reindex --verbose # With progress details
```

Use this after:
- Installing sentence-transformers
- Upgrading AI Smartness
- If embedding coverage is below 100%

### `ai daemon`

Control the background daemon:
```bash
ai daemon           # Show status (default)
ai daemon status    # Show status
ai daemon start     # Start daemon
ai daemon stop      # Stop daemon
```

The daemon also runs automatic pruning every 5 minutes:
- Applies decay to threads and bridges
- Suspends low-weight threads
- Deletes dead bridges

### `ai mode`

View or change the operating mode:
```bash
ai mode             # Show current mode
ai mode status      # Show current mode
ai mode light       # Switch to light mode (15 threads)
ai mode normal      # Switch to normal mode (50 threads)
ai mode heavy       # Switch to heavy mode (100 threads)
ai mode max         # Switch to max mode (200 threads)
```

### `ai help`

Show all available commands:
```bash
ai help
```

---

## How Memory Works

### Capture Flow

```
You use a tool (Read, Write, etc.)
         ↓
PostToolUse hook triggers
         ↓
Content sent to daemon (fast, non-blocking)
         ↓
Daemon extracts semantics (LLM)
         ↓
Thread decision: NEW / CONTINUE / FORK / REACTIVATE
         ↓
Thread updated, bridges recalculated
```

### Injection Flow

```
You type a message
         ↓
UserPromptSubmit hook triggers
         ↓
Memory Retriever finds relevant threads (by similarity)
         ↓
Auto-reactivation of suspended threads if relevant
         ↓
Context string built:
  - Current thread title + summary
  - Related threads (via bridges)
  - User rules
         ↓
Injected as invisible <system-reminder>
         ↓
Claude receives your message + context
```

### Automatic Thread Reactivation

When you mention a topic related to a suspended thread, the system can automatically reactivate it:

| Similarity | Action |
|------------|--------|
| > 0.35 | Auto-reactivate (high confidence) |
| 0.15 - 0.35 | LLM Haiku decides (borderline) |
| < 0.15 | No reactivation |

**Example:** If you worked on "AI memory system" yesterday (now suspended), and today you ask:
> "tell me about the meta cognition layer"

The system:
1. Calculates similarity with "AI memory system" (borderline: 0.28)
2. Consults Haiku: "Is this related to this thread?"
3. Haiku confirms the semantic relationship
4. Reactivates the thread
5. Injects the context into your conversation

**Slot Liberation:** If you're at max active threads (e.g., 100/100), the system automatically suspends the least important active thread to make room for the reactivated one.

### Neural Decay System

Threads and bridges use a neural-inspired weight system (Hebbian learning):

| Action | Effect on Weight |
|--------|------------------|
| New thread | Starts at 1.0 |
| Fork thread | Inherits parent's weight |
| Each use (message) | +0.1 boost (max 1.0) |
| Time decay | Halves every 7 days |
| Below 0.1 | Thread auto-suspended |
| Below 0.05 | Bridge auto-deleted |

This ensures:
- Frequently used threads stay active
- Dormant threads are auto-suspended (never deleted)
- Dead bridges are cleaned up automatically

### What Gets Injected

Example injection (invisible to you):
```xml
<system-reminder>
AI Smartness Memory Context:

Current thread: "JWT Authentication"
Summary: Implementing refresh token rotation with Redis storage.

Related threads:
- "Database Schema" - User and session tables
- "Security Audit" - Token expiration policies

User rules:
- always make a plan before implementation
- use TypeScript strict mode
</system-reminder>

Your actual message here...
```

---

## Best Practices

### Let It Work

Don't try to "help" the system:
- Work normally
- The system captures everything automatically
- Threads form naturally based on your work

### Express Preferences

Tell the agent your rules:
- "remember: I prefer functional programming"
- "rule: always add tests for new functions"
- "never use any as a type"

These get stored and applied to all future sessions.

### Check Health Regularly

```bash
ai health
```

- Continuation rate below 10%? Check embeddings
- Daemon stopped? Run `ai daemon start`
- Embedding coverage below 100%? Run `ai reindex`

### Session Resumption

When starting a new session:
1. Memory is injected automatically
2. Check status: `ai status`
3. Your agent "remembers" previous context

---

## Configuration

### Location

`ai_smartness/.ai/config.json`

### Key Settings

```json
{
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100
  },
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true,
    "require_all_choices": true
  }
}
```

### Mode Comparison

| Mode | Thread Limit | Best For |
|------|--------------|----------|
| MAX | 200 | Complex projects, 15+ hour sessions |
| heavy | 100 | Large codebases, long projects |
| normal | 50 | Medium projects |
| light | 15 | Small scripts, quick tasks |

The **MAX** mode is recommended for:
- Projects with many interdependent components
- Very long work sessions (15+ hours)
- Cases where memory loss would be critical

---

## Troubleshooting

### "Daemon not running"

```bash
ai daemon start
```

If it fails, check logs:
```bash
cat ai_smartness/.ai/daemon_stderr.log
```

### "Heuristic fallback" in titles

Claude CLI not found. Check:
```bash
which claude
```

Update path in config if needed.

### Low continuation rate

Threads not consolidating? Check:
1. Is sentence-transformers installed?
   ```bash
   python3 -c "import sentence_transformers; print('OK')"
   ```
2. If not: `pip install sentence-transformers`
3. Restart daemon: `ai daemon stop && ai daemon start`
4. Reindex: `ai reindex`

### Memory not being injected

Check injection logs:
```bash
tail -20 ai_smartness/.ai/inject.log
```

Should show lines like:
```
[2026-01-29 15:30:22] Injected: 450 chars (380 memory) for: How do I...
```

### Hooks not triggering

Check `.claude/settings.json`:
- Paths must be **absolute**
- Python3 must be in PATH

---

## Files Reference

| File | Purpose |
|------|---------|
| `.ai/config.json` | Configuration |
| `.ai/user_rules.json` | Your stored rules |
| `.ai/processor.pid` | Daemon process ID |
| `.ai/processor.sock` | Daemon socket |
| `.ai/processor.log` | Daemon logs |
| `.ai/inject.log` | Injection logs |
| `.ai/db/threads/*.json` | Thread data |
| `.ai/db/bridges/*.json` | Bridge data |
| `.ai/db/synthesis/*.json` | Compaction syntheses |

---

## What AI Smartness Does NOT Do

| Feature | Why Not |
|---------|---------|
| Require user action | 100% transparent |
| Store code content | Only semantics, not full code |
| Send data externally | 100% local |
| Modify your code | Read-only memory system |
| Require configuration | Works out of the box |

---

## Support

If you encounter issues:
1. Run `ai health` to diagnose
2. Check logs in `ai_smartness/.ai/`
3. Verify hooks in `.claude/settings.json`
4. Try `ai daemon stop && ai daemon start`
