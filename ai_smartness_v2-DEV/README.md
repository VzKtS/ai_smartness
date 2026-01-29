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
- **Memory Injection** = Context restoration at each prompt

The system maintains a **thought network** where concepts remain connected and accessible, avoiding the context loss typical of classic LLM interactions.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Threads** | Semantic work units with auto-generated titles |
| **ThinkBridges** | Automatic connections between related threads |
| **Gossip Propagation** | Bridges spread through the network when concepts evolve |
| **Memory Injection** | Relevant context injected into every prompt |
| **User Rules** | Automatic detection and persistence of user preferences |
| **GuardCode** | Plan mode enforcement, drift protection |
| **95% Synthesis** | Automatic context preservation before compaction |
| **Daemon Architecture** | Background processing for fast response |
| **100% Transparent** | Zero user action required |

---

## Installation

```bash
# Clone or copy ai_smartness_v2-DEV to your machine
# Then run install in your target project:
/path/to/ai_smartness_v2-DEV/install.sh /path/to/your/project
```

### What the Installer Does

1. **Language selection**: English, French, or Spanish
2. **Mode selection**: Heavy, Normal, or Light (affects thread limits)
3. **Installs sentence-transformers** (if not already installed)
4. **Detects Claude CLI** path for LLM extraction
5. **Copies files** to `your_project/ai_smartness_v2/`
6. **Configures hooks** with absolute paths in `.claude/settings.json`
7. **Initializes database** in `ai_smartness_v2/.ai/db/`
8. **Installs CLI** to `~/.local/bin/ai`

### Requirements

- Python 3.10+
- Claude Code (CLI or VS Code extension)
- pip (for automatic sentence-transformers install)

The installer handles dependencies automatically. If sentence-transformers fails to install, the system falls back to TF-IDF (functional but less accurate).

---

## CLI Commands

After installation, use the `ai` command from your project directory:

```bash
# Status overview
ai status

# List threads
ai threads
ai threads --status active
ai threads --status suspended
ai threads --limit 20

# View specific thread
ai thread <thread_id>

# List bridges
ai bridges
ai bridges --thread <thread_id>

# Semantic search
ai search "authentication"

# System health check
ai health

# Recalculate embeddings
ai reindex

# Daemon control
ai daemon           # Show status
ai daemon status    # Show status
ai daemon start     # Start daemon
ai daemon stop      # Stop daemon
```

---

## How It Works

### 1. Capture (PostToolUse hook)

Every tool result (Read, Write, Task, etc.) is sent to the daemon:
```
[Tool Result] → [Daemon] → [Noise Filter] → [LLM Extraction] → [Thread Decision]
```

### 2. Thread Management

The system decides for each input:
- **NEW_THREAD**: Different topic → create new thread
- **CONTINUE**: Same topic → add to active thread (similarity > 0.35)
- **FORK**: Sub-topic → create child thread
- **REACTIVATE**: Old topic returns → wake up suspended thread (similarity > 0.50)

### 3. Gossip Propagation

When a thread changes:
```
Thread A modified → Recalculate embedding
                  → For each connected thread B
                  → If similarity high → propagate bridges to B's connections
```

### 4. Memory Injection (UserPromptSubmit hook)

Before each user prompt, relevant context is injected:
```xml
<system-reminder>
AI Smartness Memory Context:

Current thread: "Authentication System"
Summary: Implementing JWT-based auth with refresh tokens...

Related threads:
- "Database Schema" - User table design
- "API Endpoints" - Auth routes

User rules:
- always make a plan before implementation
</system-reminder>
```

The user sees nothing - this is invisible to you but visible to the agent.

### 5. User Rules Detection

The system automatically detects and stores user preferences:
- "remember: always use TypeScript"
- "rule: no console.log in production"
- "always make a plan before implementation"
- "never commit directly to main"

Rules are stored in `ai_smartness_v2/.ai/user_rules.json` and injected into every prompt.

### 6. Synthesis (PreCompact hook)

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
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
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
| Heavy | 100 | Large/complex projects |

### Similarity Thresholds

| Context | Threshold | Description |
|---------|-----------|-------------|
| Active thread continuation | 0.35 | Minimum to continue a thread |
| Suspended reactivation | 0.50 | Minimum to wake a thread |
| Topic boost | +0.15 | Bonus for exact topic match |

---

## Database Structure

```
ai_smartness_v2/.ai/
├── config.json           # Configuration
├── user_rules.json       # User-defined rules
├── processor.pid         # Daemon PID
├── processor.sock        # Daemon socket
├── processor.log         # Daemon logs
├── inject.log            # Injection logs
└── db/
    ├── threads/          # Thread JSON files
    ├── bridges/          # ThinkBridge JSON files
    └── synthesis/        # Compaction syntheses
```

---

## Troubleshooting

### Daemon not running

```bash
ai daemon status
# If stopped:
ai daemon start
```

### Captures not working

Check hook paths in `.claude/settings.json` - they must be **absolute paths**.

### "Heuristic fallback" in thread titles

Claude CLI not found or not responding:
```bash
which claude
# Update path in ai_smartness_v2/.ai/config.json if needed
```

### Low similarity scores / Poor memory

sentence-transformers not installed:
```bash
pip install sentence-transformers
ai daemon stop
ai daemon start
ai reindex
```

### Low continuation rate

Check with `ai health`. If below 10%:
1. Verify sentence-transformers is installed
2. Run `ai reindex` to recalculate embeddings
3. Check `ai_smartness_v2/.ai/processor.log` for errors

---

## Architecture

### Components

| Component | File | Role |
|-----------|------|------|
| Daemon | `daemon/processor.py` | Background processing |
| Client | `daemon/client.py` | Fast communication with daemon |
| Capture Hook | `hooks/capture.py` | PostToolUse capture |
| Inject Hook | `hooks/inject.py` | UserPromptSubmit injection |
| Compact Hook | `hooks/compact.py` | PreCompact synthesis |
| Memory Retriever | `intelligence/memory_retriever.py` | Context retrieval |
| Thread Manager | `intelligence/thread_manager.py` | Thread lifecycle |
| Gossip | `intelligence/gossip.py` | Bridge propagation |
| Embeddings | `processing/embeddings.py` | Vector embeddings |

### Hooks

| Hook | Script | Trigger |
|------|--------|---------|
| `UserPromptSubmit` | inject.py | Before each user message |
| `PostToolUse` | capture.py | After each tool use |
| `PreCompact` | compact.py | At 95% context |

---

## License

MIT

---

**Note**: AI Smartness v2 is designed to be invisible. The best indication it's working is that your agent "remembers" context across sessions without you doing anything special.
