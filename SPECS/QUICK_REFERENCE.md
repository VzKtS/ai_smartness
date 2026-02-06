# AI Smartness v6.3.0 - Quick Reference

## Recall Actif (v4.0)

Agent-initiated memory queries:
```python
Read(".ai/recall/<query>")  # Search memory
Read(".ai/recall/thread_xxx")  # Direct thread access
```

**Limits:** 5 threads, 100 char summary, 8000 char max context

**Reactivation:** Suspended threads with sim > 0.5 auto-reactivate

## Heartbeat (v4.1)

Temporal awareness via beats (5min intervals):
```json
{"beat": 847, "since_last": 2}
```

| since_last | Meaning |
|------------|---------|
| 0-2 | Active conversation |
| 3-12 | Short pause (15min-1h) |
| 13-72 | Session interrupted |
| 73+ | Long absence |

## Seuils Clés

| Contexte | Seuil | Action |
|----------|-------|--------|
| Continue thread actif | > 0.35 | CONTINUE |
| Nouveau thread | < 0.35 | NEW_THREAD |
| Réactivation suspendu | > 0.50 | REACTIVATE |
| Réactivation auto | > 0.35 | Sans LLM |
| Réactivation borderline | 0.15-0.35 | LLM décide |
| Gossip bridge | > 0.50 | Créer |
| Coherence child | > 0.60 | FORK enfant |
| Coherence orphan | 0.30-0.60 | Thread normal |
| Coherence forget | < 0.30 | Ignorer |

## Formules

**Similarité:**
```
sim = 0.7×embedding + 0.3×topic_overlap + 0.15 (si topic match)
```

**Poids thread (decay exponentiel):**
```
decay_factor = 0.5^(days_since_use / 1.5)  # Half-life 1.5 jours
weight = weight * decay_factor
```

**Boost (Hebbian):**
```
weight = min(1.0, weight + 0.1)  # +0.1 par activation
```

## Pipeline

```
PostToolUse → capture.py → daemon → ThreadManager → Gossip → Storage
UserPromptSubmit → inject.py → CLI detect → MemoryRetriever → <system-reminder>
PreToolUse (Read) → pretool.py → Recall pattern? → additionalContext
PreCompact (95%) → compact.py → Synthesis → db/synthesis/
Daemon (5min) → Prune timer → decay + heartbeat++
```

## Coherence Flow (Glob/Grep)

```
Glob/Grep → Thread + pending_context
Next content → Haiku coherence check
  >0.6: child thread (FORK)
  0.3-0.6: orphan (normal)
  <0.3: forget (skip)
```

## CLI

```bash
ai status          # Overview
ai threads         # List active
ai threads --prune # Apply decay + suspend
ai thread <id>     # Details
ai bridges         # Connections
ai bridges --prune # Apply decay + delete dead
ai search <query>  # Semantic search (active only)
ai recall <query>  # Search memory (incl. suspended) [v4.0]
ai heartbeat       # Show heartbeat status [v4.1]
ai health          # System check
ai daemon start    # Start background
ai daemon stop     # Stop
ai mode status     # Show current mode
ai mode heavy      # Change mode
ai help            # Help
```

## CLI in Prompt (v3.0.0)

Type CLI commands directly in your prompt:
```
You: ai status
Claude: [Shows memory status from CLI]
```

**Pattern:** `^ai\s+(status|threads?|bridges?|search|health|daemon|mode|help)`

## V6.3 Memory Management

```
ai_sysinfo()                 # System resource monitoring
```

**Automatic features:**
- **Hard Cap** — Thread limits enforced BEFORE creation
- **LLM Archives** — Suspended >72h -> archived with synthesis
- **Faster Decay** — Threads: 1.5d, Bridges: 1.0d half-life
- **Cognitive GuardCode** — Memory pressure reminders (>80% usage)
- **Shared Hygiene** — Orphaned SharedThreads/Subscriptions/Bridges auto-cleaned

## Fichiers Clés (base)

```
.ai/
├── config.json        # Config
├── user_rules.json    # User rules
├── heartbeat.json     # Temporal awareness [v4.1]
├── processor.sock     # Daemon socket
├── processor.pid      # Daemon PID
├── tmp/recall/        # Recall temp files [v4.0]
└── db/
    ├── threads/*.json
    ├── bridges/*.json
    └── synthesis/*.json
```
(Voir section v6.2 ci-dessous pour la structure complète avec shared/)

## Modes

| Mode | Threads max |
|------|-------------|
| light | 15 |
| normal | 50 |
| heavy | 100 |
| max | 200 |

**LLM:** All modes use generic `haiku` (version-agnostic).

## Tool → SourceType → OriginType

```
Read/Glob/Grep → read → FILE_READ
Write/Edit → write → FILE_READ
Task → task → TASK
WebFetch → fetch → FETCH
Bash → command → PROMPT
UserPrompt → prompt → PROMPT
```

## Context Tools (trigger coherence)

```python
CONTEXT_TOOLS = {"Glob", "Grep"}
```

## Anti-Loop Guard

```python
# Set pendant appels LLM internes
os.environ["AI_SMARTNESS_HOOK_RUNNING"] = "1"
```

## Bridge Weight Decay (Pruning Synaptique)

```python
HALF_LIFE_DAYS = 1.0    # Weight halves every day
DEATH_THRESHOLD = 0.05  # Bridge dies below this
USE_BOOST = 0.1         # Weight boost per use
```

**Decay Formula:**
```
weight = weight * 0.5^(days_since_use / HALF_LIFE_DAYS)
```

**CLI:**
```bash
ai bridges --show-weight  # Show weight column
ai bridges --prune        # Apply decay and remove dead bridges
```

## Thread Decay (Neuronal Dormancy)

```python
HALF_LIFE_DAYS = 1.5      # Weight halves every 1.5 days
SUSPEND_THRESHOLD = 0.1   # Auto-suspend below this
USE_BOOST = 0.1           # Weight boost per activation
```

**Différence vs Bridges:** Threads are SUSPENDED, not deleted.

**CLI:**
```bash
ai threads --show-weight  # Show weight indicators
ai threads --prune        # Apply decay and suspend low-weight threads
```

## Mode Management

| Mode | Threads max |
|------|-------------|
| light | 15 |
| normal | 50 |
| heavy | 100 |
| max | 200 |

**CLI:**
```bash
ai mode status            # Show current mode and stats
ai mode light             # Switch to light mode
ai mode normal            # Switch to normal mode
ai mode heavy             # Switch to heavy mode
ai mode max               # Switch to max mode
```

**Note:** Changing to a lower quota will auto-suspend excess threads.

## Daemon Auto-Pruning (v4.0.0)

```python
PRUNE_INTERVAL_SECONDS = 300  # Every 5 minutes
```

**Actions:**
1. Increment heartbeat counter [v4.1]
2. Apply decay to all threads
3. Suspend threads with weight < 0.1
4. Apply decay to all bridges
5. Delete bridges with weight < 0.05

## Timeouts

| Op | Timeout |
|----|---------|
| Extraction | 30s |
| Coherence | 15s |
| Synthesis | 60s |
| Socket | 0.5s |

## Limites Contenu

| Élément | Max |
|---------|-----|
| Extraction | 3000 ch |
| Coherence | 1500 ch |
| Thread | 5000 ch |
| Prompt capture | 50 ch min |
| User rules | 20 max |

## V5 Hybrid Enhancement Tools

```
ai_suggestions(context?)     # Proactive optimization suggestions
ai_compact(strategy?)        # On-demand compaction (gentle/normal/aggressive)
ai_focus(topic, weight?)     # Boost injection priority for topics
ai_unfocus(topic?)           # Clear focus
ai_pin(content, title?)      # High-priority content capture
ai_rate_context(id, useful)  # Feedback on injection quality
```

## V5.1 Full Context Continuity

```
ai_profile(action, key?, value?)  # User profile management
```

**Injection Layers (5):**
1. Session State (< 1h) → Reprise immédiate
2. Work Context → Fichiers modifiés liés aux threads
3. Pinned Content → Contenu prioritaire
4. Thread Relevance → Mémoire thématique
5. User Profile (> 1h) → Personnalisation

## V5.2 Batch Operations

```
ai_merge_batch(operations)   # Merge multiple threads at once
ai_rename_batch(operations)  # Rename multiple threads at once
ai_cleanup(mode?)            # Fix threads with bad titles
ai_rename(id, title)         # Rename single thread
```

## V6.0 Shared Cognition

```
ai_share(thread_id)          # Share thread to network
ai_unshare(shared_id)        # Remove shared thread
ai_publish(shared_id)        # Update shared snapshot
ai_discover(topics?)         # Find shared threads
ai_subscribe(shared_id)      # Subscribe to shared thread
ai_unsubscribe(shared_id)    # Unsubscribe
ai_sync(shared_id?)          # Sync subscriptions
ai_shared_status()           # Shared cognition status
```

**Inter-Agent Bridges (bilateral consent):**
```
ai_propose_bridge()          # Propose cross-agent bridge
ai_accept_bridge(id)         # Accept proposal
ai_reject_bridge(id)         # Reject proposal (24h TTL)
```

## V6.1 Bridge Management Suite

```
ai_bridges(thread_id?, relation_type?, status?)  # List/filter bridges
ai_bridge_analysis()         # Network analytics (stats, health, distribution)
```

## V6.2 Phase 3 - Advanced Shared Cognition

```
ai_recommend(limit?)         # Subscription recommendations (topic overlap)
ai_topics(agent_id?)         # Network-wide topic discovery
```

**Automatic features:**
- **Shared Context Injection** — Subscribed threads auto-injected when relevant
- **Bridge Strength** — Cross-agent usage tracking (`cross_agent_uses`)

## Fichiers Clés (v6.2)

```
.ai/
├── config.json              # Config
├── user_rules.json          # User rules
├── heartbeat.json           # Temporal awareness
├── processor.sock           # Daemon socket
├── processor.pid            # Daemon PID
├── tmp/recall/              # Recall temp files
└── db/
    ├── threads/*.json
    ├── bridges/*.json
    ├── synthesis/*.json
    ├── archives/*.json       # V6.3 LLM archives
    └── shared/              # V6.0 Shared Cognition
        ├── published/
        ├── subscriptions/
        ├── cross_bridges/
        ├── proposals/
        │   ├── outgoing/
        │   └── incoming/
        └── index.json
```
