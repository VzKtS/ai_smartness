# AI Smartness v2.6 - Quick Reference

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

**Poids thread:**
```
recency = 0.5^(heures/24)
activity = min(1.0, msgs×0.1 + activations×0.05)
weight = recency×0.6 + activity×0.4
```

## Pipeline

```
PostToolUse → capture.py → daemon → ThreadManager → Gossip → Storage
UserPromptSubmit → inject.py → MemoryRetriever → <system-reminder>
PreCompact (95%) → compact.py → Synthesis → db/synthesis/
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
ai thread <id>     # Details
ai bridges         # Connections
ai search <query>  # Semantic search
ai health          # System check
ai daemon start    # Start background
ai daemon stop     # Stop
```

## Fichiers Clés

```
.ai/
├── config.json        # Config
├── user_rules.json    # User rules
├── processor.sock     # Daemon socket
├── processor.pid      # Daemon PID
└── db/
    ├── threads/*.json
    ├── bridges/*.json
    └── synthesis/*.json
```

## Modes

| Mode | Threads max | Modèle |
|------|-------------|--------|
| light | 15 | haiku |
| normal | 50 | sonnet |
| heavy | 100 | opus |
| max | 200 | opus |

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
os.environ["AI_SMARTNESS_V2_HOOK_RUNNING"] = "1"
```

## Bridge Weight Decay (Pruning Synaptique)

```python
HALF_LIFE_DAYS = 3.0    # Weight halves every 3 days
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
HALF_LIFE_DAYS = 7.0      # Weight halves every 7 days
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
