# AI Smartness v2

**Meta-cognition layer for Claude Code agents.**

A persistent memory system that transforms Claude Code into an agent capable of maintaining semantic context across long sessions, detecting connections between concepts, and resuming work after weeks/months as if you just stepped away for coffee.

Compatible with VS Code & Claude Code CLI.

---

## Vision

AI Smartness v2 is a **neural-inspired working memory**:

- **Threads** = Neurons (active reasoning streams)
- **ThinkBridges** = Synapses (semantic connections between threads)
- **Gossip** = Signal propagation through the network

The system maintains a **thought network** where concepts remain connected and accessible, avoiding the context loss typical of classic LLM interactions.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Threads** | Semantic work units with auto-generated titles |
| **ThinkBridges** | Automatic connections between related threads |
| **Gossip Propagation** | Bridges spread through the network when concepts evolve |
| **GuardCode** | Plan mode enforcement, drift protection |
| **95% Synthesis** | Automatic context preservation before compaction |
| **100% Transparent** | Zero user action required |

---

## Architecture v2 (Simplified)

### Only 2 Entities

| Entity | Role |
|--------|------|
| **Thread** | Work unit = topic + messages + summary + embedding |
| **ThinkBridge** | Semantic connection between two threads |

### What Changed from v1

| v1 | v2 | Why |
|----|----|----|
| Fragments | Absorbed into Threads | Simpler, each message = implicit fragment |
| MemBloc | Thread.status=archived | Unified model |
| Complex graph | Embeddings + Bridges | More powerful, less overhead |
| Hardcoded thresholds | LLM decisions | Intelligent, not arbitrary |

---

## Installation

```bash
# In your target project
/path/to/ai_smartness_v2/install.sh .
```

### Interactive Setup

1. **Language**: English, French, or Spanish
2. **Mode**: Heavy, Normal, or Light (affects thread limits, not extraction cost)
3. **Database**: Keep existing data or start fresh

### What the Script Does

- Copies ai_smartness_v2 into your project
- Configures Claude Code hooks with **absolute paths**
- Detects Claude CLI path for LLM extraction
- Initializes the database structure
- Adds exclusions to .gitignore and .claudeignore

**Note**: Extraction always uses **Haiku** (economical, sufficient for semantic extraction). Your main agent can use any model (Opus, Sonnet, etc.) - they're independent.

---

## CLI Commands

```bash
# Navigate to your project
cd /your/project

# Status overview
python3 ai_smartness_v2/cli/main.py status

# List threads
python3 ai_smartness_v2/cli/main.py threads
python3 ai_smartness_v2/cli/main.py threads --status active
python3 ai_smartness_v2/cli/main.py threads --limit 20

# View specific thread
python3 ai_smartness_v2/cli/main.py thread <thread_id>

# List bridges
python3 ai_smartness_v2/cli/main.py bridges
python3 ai_smartness_v2/cli/main.py bridges --thread <thread_id>

# Semantic search
python3 ai_smartness_v2/cli/main.py search "authentication"
```

---

## How It Works

### 1. Capture (PostToolUse hook)

Every tool result (Read, Write, Task, etc.) is captured:
```
[Tool Result] → [Noise Filter] → [LLM Extraction] → [Thread Decision]
```

### 2. Thread Management

The LLM decides for each input:
- **NEW_THREAD**: Different topic → create new thread
- **CONTINUE**: Same topic → add to active thread
- **FORK**: Sub-topic → create child thread
- **REACTIVATE**: Old topic returns → wake up archived thread

### 3. Gossip Propagation

When a thread changes:
```
Thread A modified → Recalculate embedding
                  → For each connected thread B
                  → If similarity high → propagate bridges to B's connections
```

### 4. Injection (UserPromptSubmit hook)

Before each user prompt, invisible context is injected:
```html
<!-- ai_smartness: {"active_thread": "...", "decisions": [...]} -->
```

### 5. Synthesis (PreCompact hook)

At 95% context window:
- LLM generates synthesis of current state
- Decisions, open questions, active threads
- Injected after compaction
- User sees nothing

---

## Configuration

Config stored in `ai_smartness_v2/.ai/config.json`:

```json
{
  "version": "2.0.0",
  "project_name": "MyProject",
  "language": "en",
  "settings": {
    "thread_mode": "heavy",
    "auto_capture": true,
    "active_threads_limit": 100
  },
  "llm": {
    "extraction_model": "claude-3-5-haiku-20241022",
    "claude_cli_path": "/usr/local/bin/claude"
  },
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true,
    "require_all_choices": true
  }
}
```

### Mode Differences

| Mode | Thread Limit | Use Case |
|------|--------------|----------|
| Light | 15 | Small projects |
| Normal | 50 | Medium projects |
| Heavy | 100 | Large/complex projects (blockchain, enterprise) |

**Note**: Extraction model is always Haiku (economical). Mode only affects thread limits.

---

## Database Structure

```
ai_smartness_v2/.ai/
├── config.json           # Configuration
├── db/
│   ├── threads/          # Thread JSON files
│   │   └── thread_*.json
│   ├── bridges/          # ThinkBridge JSON files
│   │   └── bridge_*.json
│   └── synthesis/        # Compaction syntheses
└── processor.sock        # Daemon socket (when running)
```

---

## Claude Code Hooks

| Hook | Script | Function |
|------|--------|----------|
| `UserPromptSubmit` | inject.py | Context injection |
| `PostToolUse` | capture.py | Automatic capture |
| `PreCompact` | compact.py | 95% synthesis |

---

## GuardCode Rules

| Rule | Description |
|------|-------------|
| `enforce_plan_mode` | Block code changes without validated plan |
| `warn_quick_solutions` | Remind that simple ≠ better |
| `require_all_choices` | Must present all alternatives |

---

## Requirements

- Python 3.10+
- Claude Code (CLI or VS Code extension)
- sentence-transformers (for local embeddings)

---

## Troubleshooting

### Captures not working

Check the hook paths in `.claude/settings.json` - they must be **absolute paths**.

### Extraction showing "heuristic fallback"

Claude CLI not found. Check:
```bash
which claude
# Should return /usr/local/bin/claude or similar
```

### Too many threads

Increase limit in config:
```json
"active_threads_limit": 150
```

---

## License

MIT

---

**Note**: AI Smartness v2 is a complete rewrite focused on simplicity. The neural network metaphor is operational, not a strict neural implementation.
