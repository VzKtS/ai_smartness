# AI Smartness v6.0

**Meta-cognition layer for Claude Code agents with inter-agent memory sharing.**

A persistent memory system that transforms Claude Code into an agent capable of maintaining semantic context across long sessions, detecting connections between concepts, sharing knowledge with other agents, and resuming work after weeks/months as if you just stepped away for coffee.

Compatible with VS Code & Claude Code CLI.

---

## Philosophy: Partnership, Not Control

AI Smartness enables **partnership** between you and your agent. It provides cognitive tools - not constraints.

- **GuardCode is advisory**: Suggestions, not enforcement
- **First contacts matter**: Let concepts emerge naturally with new agents
- **Trust develops over time**: The agent learns your preferences through collaboration
- **Agent autonomy**: The agent actively manages its own cognition and context window
- **Inter-agent collaboration**: Agents can share knowledge while maintaining memory isolation

---

## Vision

AI Smartness v6.0 is a **neural-inspired working memory** with **shared cognition**:

- **Threads** = Neurons (active reasoning streams)
- **ThinkBridges** = Synapses (semantic connections between threads)
- **SharedThreads** = Published knowledge (inter-agent sharing)
- **Subscriptions** = Imported knowledge from other agents
- **InterAgentBridges** = Cross-agent semantic connections (bilateral consent)
- **Recall** = Active memory retrieval on demand
- **Memory Injection** = Context restoration at each prompt
- **Session State** = Work continuity across sessions
- **User Profile** = Persistent personalization

The system maintains a **thought network** where concepts remain connected, accessible, and shareable.

---

## Key Features v6.0

| Feature | Description |
|---------|-------------|
| **Threads** | Semantic work units with auto-generated titles |
| **ThinkBridges** | Automatic connections between related threads |
| **SharedThreads** | Publish threads to network for inter-agent sharing |
| **Subscriptions** | Subscribe to SharedThreads from other agents |
| **InterAgentBridges** | Cross-agent semantic bridges (bilateral consent, 24h TTL) |
| **MCP Tools** | Native agent tools for memory management |
| **Merge/Split** | Agent-controlled memory topology |
| **Context Tracking** | Real-time context % with adaptive throttle |
| **Session State** | Track files modified, tool history, pending tasks |
| **User Profile** | Role, preferences, context rules |
| **Layered Injection** | 5-layer priority context system |
| **Memory Isolation** | Copy-on-share, pull not push |
| **CLI in Prompt** | `ai status` directly in prompt |
| **User Rules** | Automatic detection and persistence of preferences |
| **GuardCode** | Advisory system for best practices |
| **95% Synthesis** | Automatic context preservation before compaction |
| **Daemon Architecture** | Background processing + auto-pruning |
| **100% Transparent** | Zero user action required |

---

## Agent MCP Tools (v5.2)

Your agent has access to native MCP tools:

### Core Tools
```
ai_recall(query="authentication")   # Search by keyword/topic
ai_help()                           # Agent self-documentation
ai_status()                         # Memory status
```

### Thread Management
```
ai_merge(survivor_id="t1", absorbed_id="t2")   # Merge two threads
ai_split(thread_id="t1")                        # Get split info (step 1)
ai_split(thread_id="t1", confirm=True, ...)    # Execute split (step 2)
ai_unlock(thread_id="t1")                       # Unlock split-locked thread
```

### V5 Hybrid Tools
```
ai_suggestions()              # Proactive optimization suggestions
ai_compact(strategy="normal") # On-demand compaction (gentle/normal/aggressive)
ai_focus(topic="solana")      # Boost injection priority for topics
ai_unfocus()                  # Clear focus topics
ai_pin(content="important")   # High-priority content capture
ai_rate_context(thread_id, useful=True)  # Feedback on injection quality
```

### V5.1 Context Continuity
```
ai_profile(action="view")                          # View profile
ai_profile(action="set_role", role="developer")    # Set role
ai_profile(action="add_rule", rule="Always use TypeScript")  # Add rule
```

### V5.2 Batch Operations & Auto-Optimization
```
ai_merge_batch(operations=[...])   # Merge multiple threads at once
ai_rename_batch(operations=[...])  # Rename multiple threads at once
ai_cleanup(mode="auto")            # Fix threads with bad titles
ai_cleanup(mode="interactive")     # Review before fixing
ai_rename(thread_id, new_title)    # Rename a single thread
```
**Proactive Compression:** Daemon auto-compacts when context pressure > 0.80

### V6.0 Shared Cognition (Inter-Agent Memory)
```
ai_share(thread_id)           # Share a thread to the network
ai_unshare(shared_id)         # Remove shared thread
ai_publish(shared_id)         # Publish update to subscribers
ai_discover(topics=["rust"])  # Find shared threads by topics
ai_subscribe(shared_id)       # Subscribe to a shared thread
ai_unsubscribe(shared_id)     # Unsubscribe from shared thread
ai_sync()                     # Sync all stale subscriptions
ai_shared_status()            # Show shared cognition status
```

**Memory Isolation Principles:**
- **Copy-on-share**: Publishing creates a read-only snapshot
- **Pull not push**: Subscribers explicitly pull updates via `ai_sync()`
- **No private leakage**: Only SharedThread IDs, never private thread IDs

---

## Installation

**Platform:** Linux / macOS / Windows (via WSL only)

> Hooks require absolute Unix paths. Windows native paths are not supported.

### Prerequisites (Recommended)

**sentence-transformers** requires PyTorch. We recommend installing **before** running the install script to choose your variant:

```bash
# CPU only (lighter)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers

# OR with CUDA (faster with NVIDIA GPU)
pip install torch && pip install sentence-transformers
```

### Run Installer

```bash
/path/to/ai_smartness-DEV/install.sh /path/to/your/project
```

### What the Installer Does

| Step | Action |
|------|--------|
| 1 | **Language selection** (en/fr/es) |
| 2 | **Mode selection** (MAX/Heavy/Normal/Light → thread limits) |
| 3 | **Migration** from legacy `ai_smartness_v2` if present |
| 4 | **Copy files** to `project/ai_smartness/` |
| 5 | **Initialize database** (threads, bridges, synthesis dirs) |
| 6 | **Initialize heartbeat.json** (session tracking) |
| 7 | **Check sentence-transformers** (auto-install if missing) |
| 8 | **Detect Claude CLI** path |
| 9 | **Create config.json** |
| 10 | **Configure hooks** (4 hooks with absolute paths) |
| 11 | **Configure MCP server** (ai-smartness MCP tools) |
| 12 | **Configure .gitignore/.claudeignore** |
| 13 | **Install CLI** to `~/.local/bin/ai` |
| 14 | **Start daemon** (background processor) |

### The Daemon

A background daemon handles:
- Asynchronous capture processing
- LLM extraction for thread decisions
- Auto-pruning every 5 minutes

```bash
ai daemon status/start/stop
```

### Requirements

- Python 3.10+
- Claude Code (CLI or VS Code extension)
- sentence-transformers (auto-installed or pre-installed)

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

### 3. Active Recall (v4.4)
```
ai_recall(query="authentication")
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
  "version": "6.0.2",
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100,
    "shared_cognition": {
      "enabled": true,
      "auto_notify_mcp_smartness": true,
      "bridge_proposal_ttl_hours": 24,
      "default_visibility": "network"
    }
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
1. Mention `ai_recall()` exists
2. Point to `ai_help()`
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
    ├── synthesis/
    └── shared/           # v6.0 Shared Cognition
        ├── published/    # SharedThreads owned by this agent
        ├── subscriptions/# Subscriptions to other agents' SharedThreads
        ├── cross_bridges/# InterAgentBridges (bilateral consent)
        └── proposals/    # Pending bridge proposals
            ├── outgoing/
            └── incoming/
```

---

## License

MIT

---

**Note**: AI Smartness is designed to be invisible. The best indication it's working is that your agent becomes a better collaborator over time - not that nothing ever goes wrong.
