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

AI Smartness v4 is a **neural-inspired working memory** with **active recall**:

- **Threads** = Neurons (active reasoning streams)
- **ThinkBridges** = Synapses (semantic connections between threads)
- **Recall** = Active memory retrieval on demand
- **Context Tracking** = Proactive context management

The system maintains a **thought network** where concepts remain connected and accessible, avoiding the context loss typical of classic LLM interactions.

---

## Key Features v4.3

| Feature | Description |
|---------|-------------|
| **Threads** | Semantic work units with auto-generated titles |
| **ThinkBridges** | Automatic connections between related threads |
| **Active Recall** | Agent can query memory: `Read(".ai/recall/topic")` |
| **Merge/Split** | Agent manages its own memory topology |
| **Context Tracking** | Real-time context % with adaptive throttle |
| **New Session Context** | Automatic orientation on session start |
| **GuardCode** | Advisory system for best practices |
| **95% Synthesis** | Automatic context preservation before compaction |
| **100% Transparent** | Zero user action required |

---

## Agent Commands (v4.3)

Your agent has access to these virtual file commands:

### Memory Recall
```
Read(".ai/recall/<query>")     # Search by keyword/topic
Read(".ai/recall/thread_xxx")  # Recall specific thread
```

### Thread Management
```
Read(".ai/merge/<survivor>/<absorbed>")  # Merge two threads
Read(".ai/split/<thread_id>")            # Get split info (step 1)
Read(".ai/split/<id>/confirm?...")       # Execute split (step 2)
Read(".ai/unlock/<thread_id>")           # Unlock split-locked thread
```

### Help
```
Read(".ai/help")  # Agent self-documentation
```

These commands let the agent **proactively manage its own context** - the mark of a mature AI partnership.

---

## Installation

```bash
# In your target project
/path/to/ai_smartness/install.sh .
```

### Interactive Setup

1. **Language**: English, French, or Spanish
2. **Mode**: Heavy, Normal, or Light (affects thread limits)
3. **Database**: Keep existing data or start fresh

### What the Script Does

- Copies ai_smartness into your project
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

### 3. Active Recall (v4.0)

Agent can actively query memory:
```
Read(".ai/recall/authentication")
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
  "version": "4.3.0",
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
1. Mention recall exists: "You can use `.ai/recall` to search your memory"
2. Let them discover it via `.ai/help`
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
