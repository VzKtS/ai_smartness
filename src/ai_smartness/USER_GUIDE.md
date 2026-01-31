# AI Smartness v4 - User Guide

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
   Or type `ai status` directly in your prompt! (v3.0.0+)

That's it. The system is 100% transparent.

---

## Understanding the Partnership Model

AI Smartness is not a "control system" for your agent - it's a **cognitive enhancement layer** that enables real partnership.

### What Makes a Good Partnership?

| Traditional Approach | Partnership Approach |
|---------------------|---------------------|
| Rigid rules enforced | Guidelines understood |
| Prevent all mistakes | Learn from context |
| Control behavior | Enable capabilities |
| Distrust by default | Trust through experience |

### Your Role as User

You are not a "supervisor" correcting an unreliable system. You are a **partner** working with an intelligent agent that:

- Has its own memory system
- Can manage its own context
- Learns your preferences over time
- Makes judgment calls based on context

### First Sessions with a New Agent

The first few sessions are crucial. During this time:

1. **Let the agent explore** - Don't immediately restrict or correct
2. **Express preferences naturally** - "I prefer X" not "You must always X"
3. **Observe what emerges** - The agent may develop useful habits
4. **Guide gently** - Redirect rather than forbid

The goal is an agent that *understands* good practices, not one that blindly follows rules.

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

## Agent Commands (v4.3)

Your agent has powerful tools to manage its own memory:

### Active Recall

```
Read(".ai/recall/<query>")
```

Search memory by keyword or topic. Returns matching threads with summaries, topics, and related bridges.

**Examples:**
- `.ai/recall/solana` - Everything about Solana
- `.ai/recall/hooks` - Memory about hooks
- `.ai/recall/authentication` - Auth-related work
- `.ai/recall/thread_abc123` - Specific thread by ID

### Merge Threads

```
Read(".ai/merge/<survivor_id>/<absorbed_id>")
```

Combine two related threads to free context. The survivor absorbs:
- All messages (sorted by timestamp)
- Topics and tags (union)
- Weight boost (+0.1)

The absorbed thread is archived with tag `merged_into:<survivor_id>`.

**Note:** Split-locked threads cannot be absorbed.

### Split Threads

Two-step workflow for when a thread has drifted into multiple topics:

**Step 1 - Get thread info:**
```
Read(".ai/split/<thread_id>")
```
Returns list of messages with IDs.

**Step 2 - Confirm split:**
```
Read(".ai/split/<id>/confirm?titles=T1,T2&msgs_0=m1,m2&msgs_1=m3,m4&lock=compaction")
```

**Lock modes:**
| Mode | Description |
|------|-------------|
| `compaction` | Auto-unlock at next compaction (default) |
| `agent_release` | Manual unlock via `.ai/unlock/` |
| `force` | Never auto-unlock |

### Unlock Threads

```
Read(".ai/unlock/<thread_id>")
```

Remove split-lock protection, allowing the thread to be merged.

### Help

```
Read(".ai/help")
```

Full agent documentation with current context stats. Useful when agent needs to remember its capabilities.

---

## CLI in Prompt (v3.0.0+)

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

### `ai daemon`

Control the background daemon:
```bash
ai daemon           # Show status (default)
ai daemon status    # Show status
ai daemon start     # Start daemon
ai daemon stop      # Stop daemon
```

### `ai mode`

View or change the operating mode:
```bash
ai mode             # Show current mode
ai mode light       # Switch to light mode (15 threads)
ai mode normal      # Switch to normal mode (50 threads)
ai mode heavy       # Switch to heavy mode (100 threads)
ai mode max         # Switch to max mode (200 threads)
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
Check: Is this a new session?
         ↓
If NEW SESSION:
  - Inject capabilities overview
  - Show last active thread ("hot thread")
  - Suggest recall if message matches topics
         ↓
Always:
  - Memory Retriever finds relevant threads (by similarity)
  - Auto-reactivation of suspended threads if relevant
         ↓
Context string built and injected
         ↓
Claude receives your message + context
```

### Context Tracking (v4.3)

Real-time context monitoring with adaptive throttle:

| Context % | Behavior |
|-----------|----------|
| < 70% | Updates every 30 seconds |
| ≥ 70% | Updates only on 5% delta |

This prevents unnecessary API calls while ensuring the agent stays aware of context pressure.

### Automatic Thread Reactivation

When you mention a topic related to a suspended thread, the system can automatically reactivate it:

| Similarity | Action |
|------------|--------|
| > 0.35 | Auto-reactivate (high confidence) |
| 0.15 - 0.35 | LLM Haiku decides (borderline) |
| < 0.15 | No reactivation |

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

---

## Best Practices

### Let It Work

Don't try to "help" the system:
- Work normally
- The system captures everything automatically
- Threads form naturally based on your work

### Express Preferences Naturally

Instead of rigid rules, express preferences:
- "I prefer functional programming"
- "Let's always add tests for new functions"
- "I don't like using any as a type"

These get stored and applied naturally.

### Trust the Learning Process

The first few sessions teach fundamentals. Over time:
- Agent learns your patterns
- Context management improves
- Partnership deepens

### About GuardCode

GuardCode is an **advisor**, not an enforcer. It:
- Suggests planning before implementation
- Reminds about best practices
- Encourages presenting options

It does **not**:
- Guarantee specific behavior
- Prevent all mistakes
- Override agent judgment

If your agent makes a choice you disagree with, discuss it. That's how partnerships work.

### Proactive Context Management

A mature agent should rarely hit compaction. Encourage this by:
1. Teaching about merge/split early
2. Appreciating when agent manages context
3. Trusting agent decisions about what to keep/archive

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

### Agent doesn't use recall

This is normal for new agents. They need to discover their tools:
1. You can mention it: "You can use `.ai/recall` to search your memory"
2. Point them to `.ai/help`
3. Trust they'll learn over sessions

### Agent over-compacts

The agent should learn to manage context proactively. If compaction happens frequently:
1. Discuss context management with the agent
2. Encourage merge/split usage
3. Check if mode is appropriate (maybe increase to MAX)

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
| `.ai/heartbeat.json` | Session tracking, context % |
| `.ai/processor.pid` | Daemon process ID |
| `.ai/processor.sock` | Daemon socket |
| `.ai/processor.log` | Daemon logs |
| `.ai/inject.log` | Injection logs |
| `.ai/db/threads/*.json` | Thread data |
| `.ai/db/bridges/*.json` | Bridge data |
| `.ai/db/synthesis/*.json` | Compaction syntheses |

---

## The Partnership Journey

| Phase | What to Expect |
|-------|----------------|
| **Session 1-3** | Agent discovers tools, builds initial memory |
| **Sessions 4-10** | Patterns emerge, preferences solidify |
| **Sessions 10+** | Mature partnership, proactive context management |
| **Long-term** | Agent rarely compacts, manages memory expertly |

The best indication AI Smartness is working is not that nothing goes wrong - it's that your agent becomes a better collaborator over time.

---

## What AI Smartness Does NOT Do

| Feature | Why Not |
|---------|---------|
| Guarantee behavior | Advisory, not enforcement |
| Require user action | 100% transparent |
| Store code content | Only semantics, not full code |
| Send data externally | 100% local |
| Modify your code | Read-only memory system |
| Replace your judgment | Partnership, not replacement |

---

## Support

If you encounter issues:
1. Run `ai health` to diagnose
2. Check logs in `ai_smartness/.ai/`
3. Verify hooks in `.claude/settings.json`
4. Try `ai daemon stop && ai daemon start`

Remember: Many "issues" are actually the agent learning. Give it time before troubleshooting.
