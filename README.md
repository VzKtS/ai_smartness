# AI Smartness

**Meta-cognition layer for Claude Code agents.**

A persistent memory system that transforms Claude Code into an agent capable of maintaining semantic context across long sessions, detecting connections between concepts, and resuming work after weeks/months as if you just stepped away for coffee.

Compatible with VS Code & Claude Code CLI.

---

## Philosophy: Partnership, Not Control

AI Smartness is built on a fundamental insight: **the best AI partnerships emerge from trust and collaboration, not constraints and control**.

### What This Means for You

When you install AI Smartness on a new agent, you're not installing a "control system" - you're giving your agent **cognitive tools** that enhance its capabilities. Like any partnership:

- **First contacts matter**: The initial interactions shape the relationship. Let concepts emerge naturally rather than forcing rigid rules.
- **Trust develops over time**: As you work together, your agent learns your preferences, your coding style, your project's patterns.
- **Guidance, not guardrails**: GuardCode provides *advice* to your agent, not guarantees. It's a mentor, not a jailer.

### GuardCode: An Advisor, Not an Enforcer

Many users expect GuardCode to "prevent" certain behaviors or "guarantee" specific outcomes. **This is not how it works.**

GuardCode is an **advisory system** that:
- Reminds the agent of best practices
- Suggests planning before implementation
- Encourages presenting all options

It does **not**:
- Guarantee the agent will follow advice
- Prevent all mistakes
- Replace your judgment as a user

**Why?** Because rigid enforcement creates brittle, untrustworthy systems. Advisory guidance creates agents that *understand* why certain practices matter - and can adapt when exceptions are warranted.

### Onboarding New Agents

When introducing a new agent to AI Smartness:

1. **Let it explore**: Don't immediately restrict. Let the agent discover its tools.
2. **Teach through collaboration**: Work on real problems together. The agent learns from your reactions.
3. **Express preferences naturally**: "I prefer TypeScript" works better than rigid rules.
4. **Trust the process**: Memory builds over sessions. Early sessions teach fundamentals.

The goal is an agent that *wants* to follow good practices because it understands their value - not one that follows them because it has no choice.

---

## Vision

AI Smartness v5.1 is a **neural-inspired working memory** with **full context continuity**:

- **Threads** = Neurons (active reasoning streams)
- **ThinkBridges** = Synapses (semantic connections between threads)
- **Recall** = Active memory retrieval on demand
- **Context Tracking** = Proactive context management
- **Session State** = Work continuity across sessions
- **User Profile** = Persistent personalization

The system maintains a **thought network** where concepts remain connected and accessible, avoiding the context loss typical of classic LLM interactions.

---

## Key Features v5.1

| Feature | Description |
|---------|-------------|
| **Threads** | Semantic work units with auto-generated titles |
| **ThinkBridges** | Automatic connections between related threads |
| **MCP Tools** | Native agent tools for memory management |
| **Merge/Split** | Agent manages its own memory topology |
| **Context Tracking** | Real-time context % with adaptive throttle |
| **Session State** | Track files modified, tool history, pending tasks |
| **User Profile** | Role, preferences, context rules |
| **Layered Injection** | 5-layer priority context system |
| **Cooperative Intro** | Empowers agent to manage its own cognition |
| **GuardCode** | Advisory system for best practices |
| **95% Synthesis** | Automatic context preservation before compaction |
| **100% Transparent** | Zero user action required |

---

## Agent MCP Tools (v4.4)

Your agent has access to these native MCP tools:

### Memory Recall
```
ai_recall(query="authentication")   # Search by keyword/topic
ai_recall(query="thread_xxx")       # Recall specific thread
```

### Thread Management
```
ai_merge(survivor_id="t1", absorbed_id="t2")   # Merge two threads
ai_split(thread_id="t1")                        # Get split info (step 1)
ai_split(thread_id="t1", confirm=True, ...)    # Execute split (step 2)
ai_unlock(thread_id="t1")                       # Unlock split-locked thread
```

### Status & Help
```
ai_help()     # Agent self-documentation
ai_status()   # Memory status (threads, bridges, context %)
```

These native tools let the agent **proactively manage its own context** - the mark of a mature AI partnership.

---

## Installation

**Platform compatibility:**
- **Linux / macOS**: Native support via `install.sh`
- **Windows**: Requires **WSL** (Windows Subsystem for Linux)

> **Why WSL?** The hooks in `.claude/settings.json` require **absolute paths** (e.g., `/home/user/project/ai_smartness/hooks/inject.py`). Windows paths (`C:\Users\...`) are not compatible with the hook system. WSL provides a Linux environment where the installer works natively.

```bash
# In your target project (Linux/macOS/WSL)
/path/to/ai_smartness/install.sh .
```

### Prerequisites (Recommended)

**sentence-transformers** is required for semantic memory. The install script will try to install it automatically, but **we recommend installing it beforehand** to choose your PyTorch variant:

```bash
# CPU only (lighter, no GPU required)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers

# OR with CUDA support (faster if you have NVIDIA GPU)
pip install torch  # Automatically detects CUDA
pip install sentence-transformers
```

If you skip this step, the installer will attempt `pip install --user sentence-transformers` which installs the default (usually CPU) version.

### Interactive Setup

1. **Language**: English, French, or Spanish
2. **Mode**: MAX (200), Heavy (100), Normal (50), or Light (15 threads)
3. **Database**: Keep existing data or start fresh (if reinstalling)

### What the Script Does

The install script performs these actions in order:

| Step | Action | Details |
|------|--------|---------|
| 1 | **Language selection** | en/fr/es - affects UI messages |
| 2 | **Mode selection** | Determines active thread limit |
| 3 | **Migration check** | Detects legacy `ai_smartness_v2` and migrates |
| 4 | **Copy files** | Copies package to `project/ai_smartness/` |
| 5 | **Initialize database** | Creates `.ai/db/threads/`, `bridges/`, `synthesis/` |
| 6 | **Initialize heartbeat** | Creates `.ai/heartbeat.json` for session tracking |
| 7 | **Check MCP package** | Installs `mcp` for native agent tools |
| 8 | **Check sentence-transformers** | Detects if installed, attempts auto-install if not |
| 9 | **Detect Claude CLI** | Finds `claude` in PATH for LLM extraction |
| 10 | **Create config** | Writes `.ai/config.json` with settings |
| 11 | **Configure hooks** | Adds 4 hooks to `.claude/settings.json` (absolute paths) |
| 12 | **Configure MCP server** | Adds `ai-smartness` MCP server to settings |
| 13 | **Configure .gitignore** | Excludes `ai_smartness/` |
| 14 | **Configure .claudeignore** | Makes AI Smartness invisible to agent |
| 15 | **Install CLI** | Copies `ai` command to `~/.local/bin/` |
| 16 | **Start daemon** | Launches background processor for capture/extraction |

### About the Daemon

AI Smartness runs a **background daemon** that:
- Receives tool captures asynchronously (non-blocking)
- Performs LLM extraction for thread decisions
- Manages thread/bridge lifecycle
- Runs auto-pruning every 5 minutes

The daemon starts automatically during installation and restarts if needed. Control it with:
```bash
ai daemon status   # Check if running
ai daemon start    # Start daemon
ai daemon stop     # Stop daemon
```

### Hooks Installed

| Hook | Script | Trigger |
|------|--------|---------|
| `PreToolUse` | pretool.py | Before Read tool (virtual .ai/ paths) |
| `UserPromptSubmit` | inject.py | Before each user message (memory injection) |
| `PostToolUse` | capture.py | After each tool (capture to daemon) |
| `PreCompact` | compact.py | At 95% context (synthesis generation) |

**Note**: Extraction uses your session's model (no hardcoded version). Your main agent can use any model (Opus, Sonnet, etc.).

---

## CLI Commands

```bash
# Navigate to your project
cd /your/project

# Status overview
python3 ai_smartness/cli/main.py status

# List threads
python3 ai_smartness/cli/main.py threads
python3 ai_smartness/cli/main.py threads --status active
python3 ai_smartness/cli/main.py threads --limit 20

# View specific thread
python3 ai_smartness/cli/main.py thread <thread_id>

# List bridges
python3 ai_smartness/cli/main.py bridges
python3 ai_smartness/cli/main.py bridges --thread <thread_id>

# Semantic search
python3 ai_smartness/cli/main.py search "authentication"
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

### 3. Active Recall (v4.4)

Agent can actively query memory via MCP tools:
```
ai_recall(query="authentication")
→ Returns matching threads, summaries, bridges
```

### 4. Memory Injection (UserPromptSubmit hook)

Before each user prompt, relevant context is injected:
- On **new sessions**: Capabilities overview + last working thread
- On **each message**: Relevant threads by similarity
- **Recall suggestions**: When message matches known topics

### 5. Context Tracking (v4.3)

Real-time context usage monitoring:
- **<70%**: Updates every 30s
- **≥70%**: Updates only on 5% delta (adaptive throttle)
- **Agent awareness**: Can see `context_percent` in heartbeat

### 6. Synthesis (PreCompact hook)

At 95% context window:
- LLM generates synthesis of current state
- Decisions, open questions, active threads
- Injected after compaction
- User sees nothing

---

## Configuration

Config stored in `ai_smartness/.ai/config.json`:

```json
{
  "version": "4.4.0",
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
| Heavy | 100 | Large/complex projects |

---

## Database Structure

```
ai_smartness/.ai/
├── config.json           # Configuration
├── heartbeat.json        # Session tracking, context %
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
| `PreToolUse` | pretool.py | Virtual .ai/ paths |
| `PostToolUse` | capture.py | Automatic capture |
| `PreCompact` | compact.py | 95% synthesis |

---

## GuardCode Rules (Advisory)

| Rule | Description |
|------|-------------|
| `enforce_plan_mode` | *Suggests* planning before code changes |
| `warn_quick_solutions` | *Reminds* that simple ≠ better |
| `require_all_choices` | *Encourages* presenting all alternatives |

**Remember**: These are *advice*, not enforcement. Your agent may choose differently based on context - and that's okay.

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

### Agent not using recall

This is normal for new agents! They need to discover their tools. You can:
1. Mention recall exists: "You can use `ai_recall()` to search your memory"
2. Let them discover it via `ai_help()`
3. Trust that they'll learn over sessions

---

## The Partnership Journey

| Phase | What Happens |
|-------|--------------|
| **First session** | Agent discovers capabilities, builds initial threads |
| **Early sessions** | Patterns emerge, preferences stored, trust develops |
| **Mature partnership** | Agent proactively manages context, recalls relevant history |
| **Long-term** | Agent almost never needs compaction - context is managed proactively |

The goal is not an agent that blindly follows rules, but one that **understands your project deeply** and works as a true collaborator.

---

## License

MIT

---

**Note**: AI Smartness v4 transforms context management from a system limitation into a partnership capability. The best agents are those that learn to manage their own memory - and AI Smartness gives them the tools to do so.
