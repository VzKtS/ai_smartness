# AI Smartness v2 - User Guide

## Overview

AI Smartness v2 is a persistent memory system for Claude Code. It automatically captures your work context, organizes it into semantic threads, and maintains connections between related concepts.

**Key principle**: 100% transparent - you don't need to do anything special. Just work normally.

---

## Key Concepts

### Threads

A **Thread** is a semantic work unit representing a topic or task:

| Status | Description |
|--------|-------------|
| `active` | Currently being worked on |
| `suspended` | Paused, can be reactivated |
| `archived` | Completed or dormant |

Threads contain:
- **Title**: LLM-generated semantic title
- **Messages**: History of interactions
- **Summary**: LLM-generated summary
- **Embedding**: Vector for similarity search

### ThinkBridges

A **ThinkBridge** is a semantic connection between two threads.

Bridge types:
| Type | Meaning |
|------|---------|
| `extends` | A extends/refines B |
| `depends` | A depends on B |
| `contradicts` | A and B are in tension |
| `replaces` | A replaces B |
| `child_of` | A is a subtopic of B |

Bridges are created automatically when the system detects semantic similarity between threads.

### Gossip Propagation

When a thread changes, its connections **propagate** through the network:
- Thread A modified → its bridges are evaluated
- If strong similarity with connected threads → new bridges created
- Creates a "web of knowledge" that grows organically

---

## How It Works (Behind the Scenes)

### 1. Capture

Every tool result (Read, Write, Task, Bash, etc.) is captured and processed:
1. **Noise filter**: Remove IDE tags, line numbers, formatting
2. **LLM extraction**: Extract intent, subjects, questions
3. **Thread decision**: New thread? Continue existing? Fork?

### 2. Thread Management

The LLM decides what to do with each input:

| Decision | When |
|----------|------|
| `NEW_THREAD` | Different topic from active threads |
| `CONTINUE` | Same topic as active thread |
| `FORK` | Sub-topic of active thread |
| `REACTIVATE` | Old topic returns |

### 3. Context Injection

Before each of your prompts, invisible context is injected:
- Active thread info
- Recent decisions
- GuardCode reminders

You never see this, but it helps the agent maintain coherence.

### 4. 95% Synthesis

When the context window fills to 95%:
1. LLM generates a synthesis of current state
2. Key decisions, open questions, active work
3. Synthesis is injected after compaction
4. You see nothing - context is preserved

---

## CLI Commands

### Status

```bash
# Global overview
python3 .ai_smartness_v2/cli/main.py status
```

Shows:
- Thread counts by status
- Bridge count
- Last activity
- Active thread title

### Threads

```bash
# List all threads
python3 .ai_smartness_v2/cli/main.py threads

# Filter by status
python3 .ai_smartness_v2/cli/main.py threads --status active
python3 .ai_smartness_v2/cli/main.py threads --status suspended
python3 .ai_smartness_v2/cli/main.py threads --status archived

# Limit results
python3 .ai_smartness_v2/cli/main.py threads --limit 10

# View specific thread
python3 .ai_smartness_v2/cli/main.py thread thread_20260128_143022_abc123
```

### Bridges

```bash
# List all bridges
python3 .ai_smartness_v2/cli/main.py bridges

# Filter by thread
python3 .ai_smartness_v2/cli/main.py bridges --thread thread_20260128_143022

# Limit results
python3 .ai_smartness_v2/cli/main.py bridges --limit 20
```

### Search

```bash
# Semantic search across threads
python3 .ai_smartness_v2/cli/main.py search "authentication"
python3 .ai_smartness_v2/cli/main.py search "database migration"

# Limit results
python3 .ai_smartness_v2/cli/main.py search "api" --limit 5
```

---

## GuardCode

GuardCode protects your development process with configurable rules.

### Default Rules

| Rule | Effect |
|------|--------|
| `enforce_plan_mode` | Blocks code changes without a validated plan |
| `warn_quick_solutions` | Reminds that simple ≠ better |
| `require_all_choices` | Must present all alternatives |

### How It Works

Before each prompt, GuardCode checks:
1. Is there an active plan for this work?
2. Has the plan been validated by user?
3. Are there alternatives that should be presented?

If rules are violated, reminders are injected into context.

### Configuration

Edit `.ai_smartness_v2/.ai/config.json`:

```json
{
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true,
    "require_all_choices": true
  }
}
```

---

## Best Practices

### Let the System Work

Don't try to "help" the system - it captures everything automatically. Just:
- Work normally
- Make decisions explicitly when asked
- Let threads form naturally

### Session Resumption

When starting a new session:
1. The system injects context automatically
2. You can check status: `python3 .ai_smartness_v2/cli/main.py status`
3. Your agent will have access to previous context

### Long Projects

For projects spanning weeks/months:
- Threads accumulate knowledge
- Bridges connect related work
- Context is synthesized at 95%
- Resumption feels seamless

### Large Projects

For large codebases (blockchain, enterprise):
- Increase thread limit in config
- Mode "heavy" supports up to 100 threads
- Edit config to go higher if needed

---

## Configuration

### Thread Limits

```json
{
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100
  }
}
```

| Mode | Default Limit | Typical Use |
|------|---------------|-------------|
| light | 15 | Small projects |
| normal | 50 | Medium projects |
| heavy | 100 | Large/complex projects |

### Extraction Model

```json
{
  "llm": {
    "extraction_model": "claude-3-5-haiku-20241022",
    "claude_cli_path": "/usr/local/bin/claude"
  }
}
```

Extraction always uses Haiku (economical). This is independent of your main agent model.

---

## Troubleshooting

### "Heuristic fallback" in titles

The Claude CLI was not found. Check:
```bash
which claude
```

If not found, install Claude Code CLI or update the path in config.

### Captures not happening

Check hooks in `.claude/settings.json`:
- Paths must be **absolute**
- Python3 must be in PATH

### Too many threads

Increase the limit:
```json
"active_threads_limit": 150
```

### Context drift

If the agent seems to "forget" context:
1. Check thread status: active threads have context
2. Check bridges: related threads should be connected
3. The 95% synthesis preserves key info

---

## Database Files

Location: `.ai_smartness_v2/.ai/`

| File/Folder | Content |
|-------------|---------|
| `config.json` | Configuration |
| `db/threads/` | Thread JSON files |
| `db/bridges/` | Bridge JSON files |
| `db/synthesis/` | Compaction syntheses |

### Manual Inspection

```bash
# Count threads
ls .ai_smartness_v2/.ai/db/threads/ | wc -l

# Count bridges
ls .ai_smartness_v2/.ai/db/bridges/ | wc -l

# View a thread
cat .ai_smartness_v2/.ai/db/threads/thread_20260128_143022_abc123.json | python3 -m json.tool
```

---

## What v2 Does NOT Do

| Feature | Why Not |
|---------|---------|
| Require user action | 100% transparent |
| Use regex for semantics | LLM-only for meaning |
| Hardcode thresholds | LLM decides intelligently |
| Pollute your prompts | Context is invisible |
| Require configuration | Works out of the box |

---

## Support

If you encounter issues:
1. Check `.claude/settings.json` for correct hook paths
2. Verify Claude CLI is accessible
3. Review thread/bridge counts with CLI
4. Check `.ai_smartness_v2/.ai/` for database integrity
