# AI Smartness v4.0 - Specification

## Overview

Version 4.0 introduces two major features for enhanced agent autonomy:

1. **Recall Actif (v4.0)** - Agent-initiated memory queries via virtual file patterns
2. **Heartbeat (v4.1)** - Temporal awareness through abstract beat system

## Recall Actif

### Pattern

```
Read(".ai/recall/<query>")
```

### Examples

```python
Read(".ai/recall/solana validators")      # Semantic search
Read(".ai/recall/consensus mechanism")    # Topic search
Read(".ai/recall/thread_20250130_123456") # Direct thread ID
```

### Mechanism

PreToolUse hook intercepts the Read, executes memory search, and injects results via `additionalContext`. The file doesn't exist, so Read fails naturally but context is already injected.

### Implementation

| File | Role |
|------|------|
| `hooks/pretool.py` | PreToolUse hook, pattern detection |
| `hooks/recall.py` | Query handler, result formatter |
| `intelligence/memory_retriever.py` | `search()` method with suspended support |

### Output Format

```
# Memory Recall: <query>
Query executed at: 2026-01-31 10:30:00

## Matching Threads (5 found)

### [ACTIVE] Thread Title
Weight: 0.85 | Topics: topic1, topic2
Summary: Brief summary...
Last active: 2 days ago
Match score: 0.78

### [SUSPENDED] Another Thread
Weight: 0.08 | Topics: topic3
Last active: 11 days ago
-> Reactivated by this recall

## Related Bridges (3 of 5)

- Thread A -> Thread B (EXTENDS, weight: 0.65)
```

### Reactivation

Suspended threads with similarity > 0.5 are automatically reactivated:
- Status → ACTIVE
- Weight boost (+0.1)
- Marked `_reactivated: true` in output

### Limits

| Parameter | Value |
|-----------|-------|
| Threads returned | 5 max |
| Summary length | 100 chars |
| Bridges shown | 5 max |
| additionalContext | 8000 chars max |

## Heartbeat

### Concept

Abstract temporal perception for the agent. Instead of human time (10:45, Tuesday), the agent perceives "beats" - system ticks that occur every 5 minutes.

### Storage

File `.ai/heartbeat.json`:
```json
{
  "beat": 847,
  "started_at": "2026-01-15T08:00:00",
  "last_beat_at": "2026-01-31T11:15:00",
  "last_interaction_at": "2026-01-31T11:10:00",
  "last_interaction_beat": 845
}
```

### Injection

Context includes:
```json
{"beat": 847, "since_last": 2}
```

- `beat`: Global counter since system start
- `since_last`: Beats since last agent interaction

### Interpretation

| since_last | Duration (~5min/beat) | Meaning |
|------------|----------------------|---------|
| 0-2 | 0-10 min | Active conversation |
| 3-12 | 15min-1h | Short pause |
| 13-72 | 1h-6h | Session interrupted |
| 73-288 | 6h-24h | New day |
| 289+ | >24h | Long absence |

### Implementation

| File | Role |
|------|------|
| `storage/heartbeat.py` | Load/save/increment functions |
| `daemon/processor.py` | `_increment_heartbeat()` every 5min |
| `hooks/inject.py` | Include beat in context, record interaction |

## CLI Commands

```bash
ai recall <query>   # Search memory (incl. suspended)
ai heartbeat        # Show heartbeat status
```

## Hook Configuration

PreToolUse added to capture recall pattern:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {"type": "command", "command": "python3 .../hooks/pretool.py"}
        ]
      }
    ]
  }
}
```

## Files Modified

| File | Changes |
|------|---------|
| `hooks/pretool.py` | NEW - PreToolUse hook |
| `hooks/recall.py` | NEW - Recall handler |
| `storage/heartbeat.py` | NEW - Heartbeat management |
| `daemon/processor.py` | Added heartbeat increment |
| `hooks/inject.py` | Added heartbeat context injection |
| `intelligence/memory_retriever.py` | Added `search()` method |
| `install.sh` | Added PreToolUse config, heartbeat init |
| `__init__.py` | Version 4.0.0, heartbeat exports |

## Version

- **4.0.0**: Recall Actif + Heartbeat
- Breaking: New hook (PreToolUse) required

## Notes

### Why not replace Read result directly?

Claude Code PreToolUse hooks cannot replace tool results. They can only:
- Block/allow/ask permission
- Modify input parameters
- Add additional context

Solution: Use `additionalContext` to inject memory results. The Read fails (file doesn't exist) but context is available.

### Why beats instead of human time?

The agent exists intermittently between user messages. Beats provide a temporal abstraction congruent with this nature - "system time" rather than social time conventions.

### Last active vs Heartbeat

- **Heartbeat/beats**: Agent's temporal perception (system time)
- **Last active: X days ago**: Information staleness indicator (human time)

Both are complementary and serve different purposes.
