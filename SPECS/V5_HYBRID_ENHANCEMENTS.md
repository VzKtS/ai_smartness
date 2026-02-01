# V5 Hybrid Enhancements Specification

## Overview

Five MCP tools that enhance the hybrid architecture by creating bidirectional communication between explicit agent commands (MCP) and automatic background processing (hooks).

**Philosophy**: The agent guides, the system executes. These tools don't replace hooks - they give the agent influence over hook behavior.

---

## Feature 1: Focus Control

### Purpose
Agent signals current topic focus, hooks adjust injection relevance accordingly.

### MCP Tools

```python
@server.tool()
async def ai_focus(topic: str, weight: float = 0.8) -> str:
    """
    Signal focus on a topic. Hooks will prioritize related threads.

    Args:
        topic: Topic keyword or thread_id to focus on
        weight: Priority weight 0.0-1.0 (default 0.8)

    Returns:
        Confirmation with affected threads count
    """

@server.tool()
async def ai_unfocus(topic: Optional[str] = None) -> str:
    """
    Remove focus. If topic=None, clears all focus.

    Args:
        topic: Specific topic to unfocus, or None for all

    Returns:
        Confirmation
    """
```

### Storage

```json
// .ai/focus.json
{
  "active_focus": [
    {"topic": "solana", "weight": 0.8, "set_at": "2026-02-01T08:00:00"},
    {"topic": "thread_xxx", "weight": 0.6, "set_at": "2026-02-01T08:05:00"}
  ],
  "last_updated": "2026-02-01T08:05:00"
}
```

### Hook Integration

**inject.py modifications:**
```python
def get_focus_boost(thread: Thread, focus_data: dict) -> float:
    """Calculate focus-based boost for thread relevance."""
    boost = 0.0
    for focus in focus_data.get("active_focus", []):
        topic = focus["topic"]
        weight = focus["weight"]

        # Match by topic
        if topic in thread.topics:
            boost += weight * 0.3

        # Match by thread_id
        if topic == thread.id:
            boost += weight * 0.5

        # Match by title similarity
        if topic.lower() in thread.title.lower():
            boost += weight * 0.2

    return min(boost, 0.5)  # Cap at 0.5 boost
```

### Usage Example

```
Agent: ai_focus("authentication")
System: Focus set on "authentication" (weight=0.8). 3 threads will be prioritized.

[Next prompt - hooks automatically inject auth-related threads first]

Agent: ai_unfocus()
System: All focus cleared. Returning to similarity-based injection.
```

---

## Feature 2: Priority Capture

### Purpose
Agent marks specific content as high-priority for capture, ensuring important information gets stored with elevated weight.

### MCP Tool

```python
@server.tool()
async def ai_pin(
    content: str,
    title: Optional[str] = None,
    topics: Optional[List[str]] = None,
    weight_boost: float = 0.3
) -> str:
    """
    Pin important content with elevated priority.

    Creates or updates a thread with boosted weight.
    Bypasses normal coherence checking - always creates.

    Args:
        content: Content to pin (will be stored as-is)
        title: Optional title (auto-generated if not provided)
        topics: Optional topic tags
        weight_boost: Additional weight 0.0-0.5 (default 0.3)

    Returns:
        Thread ID of pinned content
    """
```

### Implementation

```python
async def ai_pin(content: str, title: str = None, topics: list = None, weight_boost: float = 0.3) -> str:
    # Clamp boost
    weight_boost = max(0.0, min(0.5, weight_boost))

    # Create thread directly (bypass coherence)
    thread = Thread(
        title=title or extract_title(content),
        messages=[Message(content=content, source="agent_pin")],
        topics=topics or [],
        weight=1.0 + weight_boost,  # Start above normal
        tags=["pinned"]
    )

    storage.save_thread(thread)

    return f"Pinned as {thread.id} (weight={thread.weight:.2f})"
```

### Usage Example

```
Agent: ai_pin("User prefers dark mode and vi keybindings", title="User Preferences", topics=["preferences", "ui"])
System: Pinned as thread_20260201_083000_abc123 (weight=1.30)
```

---

## Feature 3: Proactive Suggestions

### Purpose
System analyzes current state and provides actionable recommendations without forcing agent action.

### MCP Tool

```python
@server.tool()
async def ai_suggestions(context: Optional[str] = None) -> str:
    """
    Get proactive suggestions based on current memory state.

    Args:
        context: Optional current context/topic for targeted suggestions

    Returns:
        JSON with categorized suggestions
    """
```

### Response Format

```json
{
  "merge_candidates": [
    {
      "thread_a": "thread_xxx",
      "thread_b": "thread_yyy",
      "similarity": 0.92,
      "reason": "Both about authentication flow",
      "command": "ai_merge('thread_xxx', 'thread_yyy')"
    }
  ],
  "split_candidates": [
    {
      "thread_id": "thread_zzz",
      "reason": "Thread drifted from 'API design' to 'database schema'",
      "topics_to_split": ["database schema"],
      "command": "ai_split('thread_zzz')"
    }
  ],
  "recall_hints": [
    {
      "topic": "solana",
      "last_mentioned": "3 sessions ago",
      "thread_count": 5,
      "command": "ai_recall('solana')"
    }
  ],
  "health": {
    "active_threads": 15,
    "context_pressure": 0.73,
    "recommendation": "Consider merging similar threads to reduce pressure"
  }
}
```

### Implementation Logic

```python
async def ai_suggestions(context: str = None) -> str:
    suggestions = {
        "merge_candidates": [],
        "split_candidates": [],
        "recall_hints": [],
        "health": {}
    }

    threads = storage.get_active_threads()

    # 1. Find merge candidates (similarity > 0.85)
    for i, t1 in enumerate(threads):
        for t2 in threads[i+1:]:
            sim = cosine_similarity(t1.embedding, t2.embedding)
            if sim > 0.85:
                suggestions["merge_candidates"].append({
                    "thread_a": t1.id,
                    "thread_b": t2.id,
                    "similarity": round(sim, 2),
                    "reason": f"Similar topics: {set(t1.topics) & set(t2.topics)}",
                    "command": f"ai_merge('{t1.id}', '{t2.id}')"
                })

    # 2. Find split candidates (drift detected)
    for thread in threads:
        if len(thread.drift_history) > 3:
            unique_origins = set(thread.drift_history[-5:])
            if len(unique_origins) >= 3:
                suggestions["split_candidates"].append({
                    "thread_id": thread.id,
                    "reason": "Multiple topic shifts detected",
                    "command": f"ai_split('{thread.id}')"
                })

    # 3. Recall hints based on context
    if context:
        related = search_by_similarity(context, limit=3)
        for thread in related:
            if thread.activation_count == 0:  # Never recalled
                suggestions["recall_hints"].append({
                    "topic": thread.topics[0] if thread.topics else thread.title,
                    "thread_count": 1,
                    "command": f"ai_recall('{thread.topics[0]}')"
                })

    # 4. Health metrics
    total_weight = sum(t.weight for t in threads)
    suggestions["health"] = {
        "active_threads": len(threads),
        "context_pressure": min(1.0, total_weight / 10.0),
        "recommendation": get_health_recommendation(suggestions)
    }

    return json.dumps(suggestions, indent=2)
```

### Usage Example

```
Agent: ai_suggestions("working on authentication")
System: {
  "merge_candidates": [
    {"thread_a": "thread_auth_flow", "thread_b": "thread_login", "similarity": 0.91, ...}
  ],
  "recall_hints": [
    {"topic": "JWT tokens", "last_mentioned": "2 sessions ago", ...}
  ],
  "health": {
    "active_threads": 12,
    "context_pressure": 0.65,
    "recommendation": "Healthy state, no action needed"
  }
}
```

---

## Feature 4: Context Rating

### Purpose
Agent provides feedback on injected context quality, improving future injection relevance.

### MCP Tool

```python
@server.tool()
async def ai_rate_context(
    thread_id: str,
    useful: bool,
    reason: Optional[str] = None
) -> str:
    """
    Rate the usefulness of injected context.

    Affects future injection probability for this thread.

    Args:
        thread_id: Thread ID that was injected
        useful: True if context was helpful, False if noise
        reason: Optional explanation

    Returns:
        Confirmation with new relevance score
    """
```

### Storage

```json
// Thread JSON additions
{
  "id": "thread_xxx",
  "ratings": [
    {"useful": true, "timestamp": "2026-02-01T08:00:00", "reason": null},
    {"useful": false, "timestamp": "2026-02-01T09:00:00", "reason": "outdated info"}
  ],
  "relevance_score": 0.85  // Computed from ratings
}
```

### Relevance Score Calculation

```python
def update_relevance_score(thread: Thread, useful: bool) -> float:
    """Update thread relevance based on rating."""
    # Add rating
    thread.ratings.append({
        "useful": useful,
        "timestamp": datetime.now().isoformat(),
    })

    # Calculate score (recent ratings weighted more)
    if not thread.ratings:
        return 1.0

    total_weight = 0.0
    weighted_sum = 0.0

    for i, rating in enumerate(thread.ratings[-10:]):  # Last 10 ratings
        weight = 1.0 + (i * 0.1)  # More recent = higher weight
        total_weight += weight
        weighted_sum += weight * (1.0 if rating["useful"] else 0.0)

    return weighted_sum / total_weight if total_weight > 0 else 1.0
```

### Hook Integration

**inject.py modifications:**
```python
def calculate_injection_priority(thread: Thread, similarity: float) -> float:
    """Calculate final injection priority."""
    base_priority = similarity * thread.weight

    # Apply relevance score from ratings
    relevance = thread.relevance_score if hasattr(thread, 'relevance_score') else 1.0

    return base_priority * relevance
```

### Usage Example

```
[System injects thread about "old API design"]

Agent: ai_rate_context("thread_old_api", useful=False, reason="API was redesigned")
System: Rated thread_old_api as not useful. Relevance score: 0.85 → 0.72

[Future injections will deprioritize this thread]
```

---

## Feature 5: On-Demand Compaction

### Purpose
Agent explicitly triggers memory compaction when feeling context pressure.

### MCP Tool

```python
@server.tool()
async def ai_compact(
    strategy: Literal["gentle", "normal", "aggressive"] = "normal",
    dry_run: bool = False
) -> str:
    """
    Trigger memory compaction to reduce context pressure.

    Args:
        strategy: Compaction aggressiveness
            - gentle: Only merge very similar threads (>0.95)
            - normal: Standard compaction (>0.85 similarity, archive old)
            - aggressive: Heavy reduction (>0.75 similarity, archive more)
        dry_run: If True, show what would happen without executing

    Returns:
        Compaction report
    """
```

### Strategy Parameters

```python
COMPACTION_STRATEGIES = {
    "gentle": {
        "merge_threshold": 0.95,
        "archive_age_days": 30,
        "max_active_threads": 50,
        "weight_decay": 0.95
    },
    "normal": {
        "merge_threshold": 0.85,
        "archive_age_days": 14,
        "max_active_threads": 30,
        "weight_decay": 0.90
    },
    "aggressive": {
        "merge_threshold": 0.75,
        "archive_age_days": 7,
        "max_active_threads": 15,
        "weight_decay": 0.80
    }
}
```

### Implementation

```python
async def ai_compact(strategy: str = "normal", dry_run: bool = False) -> str:
    params = COMPACTION_STRATEGIES[strategy]
    report = {
        "strategy": strategy,
        "dry_run": dry_run,
        "actions": [],
        "before": {},
        "after": {}
    }

    threads = storage.get_all_threads()
    active = [t for t in threads if t.status == "active"]

    report["before"] = {
        "active_threads": len(active),
        "total_weight": sum(t.weight for t in active)
    }

    # 1. Merge similar threads
    merged_pairs = find_merge_candidates(active, params["merge_threshold"])
    for t1, t2 in merged_pairs:
        if not dry_run:
            merge_threads(t1.id, t2.id)
        report["actions"].append({
            "action": "merge",
            "threads": [t1.id, t2.id],
            "similarity": cosine_similarity(t1.embedding, t2.embedding)
        })

    # 2. Archive old threads
    cutoff = datetime.now() - timedelta(days=params["archive_age_days"])
    for thread in active:
        if thread.last_active < cutoff:
            if not dry_run:
                archive_thread(thread.id)
            report["actions"].append({
                "action": "archive",
                "thread": thread.id,
                "reason": "age"
            })

    # 3. Apply weight decay
    if not dry_run:
        for thread in active:
            thread.weight *= params["weight_decay"]
            storage.save_thread(thread)

    # 4. Force archive if still over limit
    remaining = storage.get_active_threads()
    if len(remaining) > params["max_active_threads"]:
        to_archive = sorted(remaining, key=lambda t: t.weight)
        excess = len(remaining) - params["max_active_threads"]
        for thread in to_archive[:excess]:
            if not dry_run:
                archive_thread(thread.id)
            report["actions"].append({
                "action": "archive",
                "thread": thread.id,
                "reason": "capacity"
            })

    # Final stats
    if not dry_run:
        final_active = storage.get_active_threads()
        report["after"] = {
            "active_threads": len(final_active),
            "total_weight": sum(t.weight for t in final_active)
        }

    return json.dumps(report, indent=2)
```

### Usage Example

```
Agent: ai_compact(strategy="aggressive", dry_run=True)
System: {
  "strategy": "aggressive",
  "dry_run": true,
  "actions": [
    {"action": "merge", "threads": ["thread_a", "thread_b"], "similarity": 0.82},
    {"action": "archive", "thread": "thread_old", "reason": "age"},
    {"action": "archive", "thread": "thread_low", "reason": "capacity"}
  ],
  "before": {"active_threads": 25, "total_weight": 18.5},
  "after": {"active_threads": 15, "total_weight": 10.2}
}

Agent: ai_compact(strategy="aggressive")  # Execute for real
System: Compaction complete. 25 → 15 active threads.
```

---

## Implementation Priority

| Feature | Complexity | Impact | Priority |
|---------|-----------|--------|----------|
| ai_suggestions | Medium | High | 1 |
| ai_compact | Medium | High | 2 |
| ai_focus/unfocus | Low | Medium | 3 |
| ai_pin | Low | Medium | 4 |
| ai_rate_context | Medium | Low | 5 |

**Recommended order**: suggestions → compact → focus → pin → rate

---

## Files to Modify

| File | Changes |
|------|---------|
| `mcp/server.py` | Add 6 new tools |
| `storage/manager.py` | Add focus.json handling, ratings field |
| `hooks/inject.py` | Integrate focus boost, relevance score |
| `models/thread.py` | Add ratings field, relevance_score |
| `processing/compaction.py` | New file for compaction logic |

---

## Backwards Compatibility

All features are additive:
- New MCP tools don't affect existing ones
- Hook modifications are conditional (check if focus/ratings exist)
- New storage files are optional (created on first use)
- Existing threads work without ratings field (default relevance=1.0)

---

## Version

**Target**: v5.0.0
**Codename**: Hybrid Enhancement Release
