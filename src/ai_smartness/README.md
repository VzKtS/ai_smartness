# AI Smartness v4

**Meta-cognition layer for Claude Code agents.**

A persistent memory system that transforms Claude Code into an agent capable of maintaining semantic context across long sessions, detecting connections between concepts, and resuming work after weeks/months as if you just stepped away for coffee.

Compatible with VS Code & Claude Code CLI.

---

## Philosophy: Partnership, Not Control

AI Smartness enables **partnership** between you and your agent. It provides cognitive tools - not constraints.

- **GuardCode is advisory**: Suggestions, not enforcement
- **First contacts matter**: Let concepts emerge naturally with new agents
- **Trust develops over time**: The agent learns your preferences through collaboration

See the main [README](../../README.md) for the full philosophy discussion.

---

## Vision

AI Smartness v4 is a **neural-inspired working memory** with **active recall**:

- **Threads** = Neurons (active reasoning streams)
- **ThinkBridges** = Synapses (semantic connections between threads)
- **Recall** = Active memory retrieval on demand
- **Memory Injection** = Context restoration at each prompt

The system maintains a **thought network** where concepts remain connected and accessible.

---

## Key Features v4.3

| Feature | Description |
|---------|-------------|
| **Threads** | Semantic work units with auto-generated titles |
| **ThinkBridges** | Automatic connections between related threads |
| **Active Recall** | `Read(".ai/recall/<query>")` - on-demand memory |
| **Merge/Split** | Agent-controlled memory topology |
| **Context Tracking** | Real-time context % with adaptive throttle |
| **New Session Context** | Automatic orientation on session start |
| **CLI in Prompt** | `ai status` directly in prompt |
| **User Rules** | Automatic detection and persistence of preferences |
| **GuardCode** | Advisory system for best practices |
| **95% Synthesis** | Automatic context preservation before compaction |
| **Daemon Architecture** | Background processing + auto-pruning |
| **100% Transparent** | Zero user action required |

---

## Agent Commands (v4.3)

Your agent can manage its own memory:

```
Read(".ai/help")                              # Self-documentation
Read(".ai/recall/<query>")                    # Search memory
Read(".ai/merge/<survivor>/<absorbed>")       # Merge threads
Read(".ai/split/<thread_id>")                 # Get split info
Read(".ai/split/<id>/confirm?...")            # Execute split
Read(".ai/unlock/<thread_id>")                # Unlock thread
```

---

## Installation

```bash
# Clone or copy ai_smartness-DEV to your machine
# Then run install in your target project:
/path/to/ai_smartness-DEV/install.sh /path/to/your/project
```

### What the Installer Does

1. **Language selection**: English, French, or Spanish
2. **Mode selection**: Heavy, Normal, or Light
3. **Installs sentence-transformers** (if needed)
4. **Detects Claude CLI** path
5. **Copies files** to `your_project/ai_smartness/`
6. **Configures hooks** with absolute paths
7. **Initializes database**
8. **Installs CLI** to `~/.local/bin/ai`

### Requirements

- Python 3.10+
- Claude Code (CLI or VS Code extension)
- pip (for automatic sentence-transformers install)

---

## CLI Commands

```bash
# Status overview
ai status

# List threads
ai threads
ai threads --status active
ai threads --prune

# View specific thread
ai thread <thread_id>

# List bridges
ai bridges
ai bridges --thread <thread_id>

# Semantic search
ai search "authentication"

# System health
ai health

# Recalculate embeddings
ai reindex

# Daemon control
ai daemon start
ai daemon stop

# Mode management
ai mode heavy
```

### In Prompt (v3.0.0+)

Type CLI commands directly:
```
You: ai status
Claude: [Shows memory status]
```

---

## How It Works

### 1. Capture (PostToolUse hook)
```
[Tool Result] → [Daemon] → [LLM Extraction] → [Thread Decision]
```

### 2. Thread Management
- **NEW_THREAD**: Different topic
- **CONTINUE**: Same topic (similarity > 0.35)
- **FORK**: Sub-topic
- **REACTIVATE**: Old topic returns (similarity > 0.50)

### 3. Active Recall (v4.0)
```
Read(".ai/recall/authentication")
→ Returns threads, summaries, bridges
```

### 4. Memory Injection (UserPromptSubmit)

New sessions get:
- Capabilities overview
- Last active thread ("hot thread")
- Recall suggestions

Each message gets:
- Relevant threads by similarity
- User rules

### 5. Context Tracking (v4.3)
- <70%: Updates every 30s
- ≥70%: Updates on 5% delta only

### 6. Synthesis (PreCompact, 95%)
Auto-generated state synthesis before compaction.

---

## Configuration

```json
{
  "version": "4.3.0",
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100
  },
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true
  }
}
```

### Modes

| Mode | Thread Limit |
|------|--------------|
| Light | 15 |
| Normal | 50 |
| Heavy | 100 |
| Max | 200 |

---

## Architecture

### Components

| Component | File | Role |
|-----------|------|------|
| Daemon | `daemon/processor.py` | Background processing |
| Client | `daemon/client.py` | Fast communication |
| Capture Hook | `hooks/capture.py` | PostToolUse |
| Inject Hook | `hooks/inject.py` | UserPromptSubmit |
| PreTool Hook | `hooks/pretool.py` | Virtual .ai/ paths |
| Recall Handler | `hooks/recall.py` | Memory recall + merge/split |
| Compact Hook | `hooks/compact.py` | PreCompact synthesis |
| Memory Retriever | `intelligence/memory_retriever.py` | Context retrieval |
| Thread Manager | `intelligence/thread_manager.py` | Thread lifecycle |
| Embeddings | `processing/embeddings.py` | Vector embeddings |

### Hooks

| Hook | Script | Function |
|------|--------|----------|
| `UserPromptSubmit` | inject.py | CLI commands + memory injection |
| `PreToolUse` | pretool.py | Virtual .ai/ paths |
| `PostToolUse` | capture.py | Thread capture |
| `PreCompact` | compact.py | Synthesis generation |

---

## Troubleshooting

### Daemon not running
```bash
ai daemon start
```

### Agent doesn't use recall
Normal for new agents. They need to discover tools:
1. Mention `.ai/recall` exists
2. Point to `.ai/help`
3. Trust the learning process

### Low similarity scores
```bash
pip install sentence-transformers
ai daemon stop && ai daemon start
ai reindex
```

---

## Database Structure

```
ai_smartness/.ai/
├── config.json
├── heartbeat.json        # Session tracking, context %
├── user_rules.json
├── processor.pid
├── processor.sock
├── processor.log
├── inject.log
└── db/
    ├── threads/
    ├── bridges/
    └── synthesis/
```

---

## License

MIT

---

**Note**: AI Smartness is designed to be invisible. The best indication it's working is that your agent becomes a better collaborator over time - not that nothing ever goes wrong.
