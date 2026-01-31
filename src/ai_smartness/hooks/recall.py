"""
Recall handler for AI Smartness v4.0.

Handles active memory recall queries triggered by Read(".ai/recall/<query>").
Searches threads and bridges, formats results for agent consumption.

Features:
- Search by query or thread ID
- Include suspended threads (with score threshold)
- Auto-reactivate suspended threads with high relevance
- Format with Last active timestamp for staleness evaluation
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Import path setup
def _setup_imports():
    """Setup import paths for package modules."""
    package_dir = Path(__file__).parent.parent
    package_parent = package_dir.parent
    if str(package_parent) not in sys.path:
        sys.path.insert(0, str(package_parent))

_setup_imports()


def handle_recall(query: str, ai_path: Path) -> str:
    """
    Handle a recall query and return formatted memory context.

    Args:
        query: Search query or thread ID
        ai_path: Path to .ai directory

    Returns:
        Formatted memory context string
    """
    try:
        from ai_smartness.intelligence.memory_retriever import MemoryRetriever

        db_path = ai_path / "db"
        retriever = MemoryRetriever(db_path)

        # Search with suspended threads included (limit 5 for compact output)
        threads, bridges = retriever.search(query, include_suspended=True, limit=5)

        # Format results
        return format_recall_result(query, threads, bridges)

    except ImportError as e:
        return f"# Memory Recall Error\n\nFailed to import MemoryRetriever: {e}"
    except Exception as e:
        return f"# Memory Recall Error\n\nError during recall: {e}"


def format_recall_result(
    query: str,
    threads: List[Dict],
    bridges: List[Dict]
) -> str:
    """
    Format recall results as readable memory context.

    Args:
        query: Original query
        threads: List of matching threads
        bridges: List of related bridges

    Returns:
        Formatted string for agent consumption
    """
    lines = [
        f"# Memory Recall: {query}",
        f"Query executed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]

    # Threads section
    if threads:
        lines.append(f"## Matching Threads ({len(threads)} found)")
        lines.append("")

        for thread in threads:
            status = thread.get("status", "active").upper()
            title = thread.get("title", "Untitled")[:60]
            weight = thread.get("weight", 0.5)
            topics = thread.get("topics", [])[:5]
            summary = thread.get("summary", "")[:100]
            last_active = thread.get("last_active", "")
            similarity = thread.get("_similarity", 0)  # Added by search()
            reactivated = thread.get("_reactivated", False)

            # Calculate "last active" human-readable
            last_active_str = _format_last_active(last_active)

            lines.append(f"### [{status}] {title}")
            lines.append(f"Weight: {weight:.2f} | Topics: {', '.join(topics)}")

            if summary:
                lines.append(f"Summary: {summary}")

            lines.append(f"Last active: {last_active_str}")

            if similarity > 0:
                lines.append(f"Match score: {similarity:.2f}")

            if reactivated:
                lines.append("-> Reactivated by this recall")

            lines.append("")

    else:
        lines.append("## No matching threads found")
        lines.append("")

    # Bridges section (limit to 5)
    if bridges:
        bridges_shown = bridges[:5]
        lines.append(f"## Related Bridges ({len(bridges_shown)} of {len(bridges)})")
        lines.append("")

        for bridge in bridges_shown:
            source_title = bridge.get("_source_title", bridge.get("source_id", "")[:8])
            target_title = bridge.get("_target_title", bridge.get("target_id", "")[:8])
            bridge_type = bridge.get("bridge_type", "RELATES")
            weight = bridge.get("weight", 0.5)

            lines.append(f"- {source_title} -> {target_title} ({bridge_type}, weight: {weight:.2f})")

        lines.append("")

    return "\n".join(lines)


def _format_last_active(iso_timestamp: str) -> str:
    """
    Format ISO timestamp as human-readable "X days ago".

    Args:
        iso_timestamp: ISO format timestamp string

    Returns:
        Human-readable string like "2 days ago"
    """
    if not iso_timestamp:
        return "unknown"

    try:
        last_active = datetime.fromisoformat(iso_timestamp)
        now = datetime.now()
        delta = now - last_active

        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                minutes = delta.seconds // 60
                return f"{minutes} minutes ago" if minutes > 1 else "just now"
            return f"{hours} hours ago" if hours > 1 else "1 hour ago"
        elif delta.days == 1:
            return "1 day ago"
        else:
            return f"{delta.days} days ago"

    except (ValueError, TypeError):
        return "unknown"


# =============================================================================
# MERGE / SPLIT / UNLOCK HANDLERS (v4.3)
# =============================================================================

def handle_merge(survivor_id: str, absorbed_id: str, ai_path: Path) -> str:
    """
    Handle a merge request: .ai/merge/<survivor_id>/<absorbed_id>

    Args:
        survivor_id: Thread to keep active
        absorbed_id: Thread to absorb and archive
        ai_path: Path to .ai directory

    Returns:
        Status message
    """
    try:
        from ai_smartness.storage.threads import ThreadStorage

        db_path = ai_path / "db"
        storage = ThreadStorage(db_path / "threads")

        merged = storage.merge(survivor_id, absorbed_id)

        if merged:
            return f"""# Merge Complete

Survivor: {merged.title} ({merged.id})
Messages: {len(merged.messages)}
Topics: {', '.join(merged.topics[:5])}

The absorbed thread has been archived with tag 'merged_into:{survivor_id}'."""
        else:
            return """# Merge Failed

Could not merge threads. Possible reasons:
- Thread not found
- Absorbed thread is split_locked (protected)"""

    except Exception as e:
        return f"# Merge Error\n\n{e}"


def handle_split_info(thread_id: str, ai_path: Path) -> str:
    """
    Handle split info request (step 1): .ai/split/<thread_id>

    Returns thread info and messages for split decision.

    Args:
        thread_id: Thread to get info for
        ai_path: Path to .ai directory

    Returns:
        Thread info with messages
    """
    try:
        from ai_smartness.storage.threads import ThreadStorage

        db_path = ai_path / "db"
        storage = ThreadStorage(db_path / "threads")

        info = storage.get_split_info(thread_id)

        if not info:
            return f"# Thread Not Found\n\nNo thread with ID: {thread_id}"

        lines = [
            f"# Split Thread: {info['title']}",
            f"ID: {info['id']}",
            f"Messages: {info['message_count']}",
            "",
            "## Messages"
        ]

        for msg in info["messages"]:
            lines.append(f"- {msg['id']} [{msg['source']}] \"{msg['preview']}\"")

        lines.extend([
            "",
            "## To split, call:",
            f"Read(\".ai/split/{thread_id}/confirm?titles=Title1,Title2&msgs_0=id1,id2&msgs_1=id3,id4&lock=compaction\")",
            "",
            "Parameters:",
            "- titles: Comma-separated titles for new threads",
            "- msgs_N: Message IDs for thread N (0-indexed)",
            "- lock: compaction (default) | agent_release | force"
        ])

        return "\n".join(lines)

    except Exception as e:
        return f"# Split Info Error\n\n{e}"


def handle_split_confirm(thread_id: str, params: Dict[str, str], ai_path: Path) -> str:
    """
    Handle split confirmation (step 2): .ai/split/<thread_id>/confirm?...

    Args:
        thread_id: Thread to split
        params: Dict with 'titles', 'msgs_0', 'msgs_1', etc., 'lock'
        ai_path: Path to .ai directory

    Returns:
        Split result message
    """
    try:
        from ai_smartness.storage.threads import ThreadStorage

        db_path = ai_path / "db"
        storage = ThreadStorage(db_path / "threads")

        # Parse parameters
        titles = params.get("titles", "").split(",")
        lock_until = params.get("lock", "compaction")

        # Build split config
        split_config = []
        for i, title in enumerate(titles):
            title = title.strip()
            if not title:
                continue

            msg_key = f"msgs_{i}"
            message_ids = [m.strip() for m in params.get(msg_key, "").split(",") if m.strip()]

            if message_ids:
                split_config.append({
                    "title": title,
                    "message_ids": message_ids
                })

        if not split_config:
            return "# Split Failed\n\nNo valid split configuration provided."

        # Execute split
        new_threads = storage.split(thread_id, split_config, lock_until)

        if new_threads:
            lines = [
                "# Split Complete",
                f"Created {len(new_threads)} new threads:",
                ""
            ]
            for t in new_threads:
                lines.append(f"- {t.title} ({t.id}) - {len(t.messages)} messages")
                lines.append(f"  split_locked_until: {t.split_locked_until}")

            return "\n".join(lines)
        else:
            return "# Split Failed\n\nNo threads were created. Check message IDs."

    except Exception as e:
        return f"# Split Error\n\n{e}"


def handle_unlock(thread_id: str, ai_path: Path) -> str:
    """
    Handle unlock request: .ai/unlock/<thread_id>

    Args:
        thread_id: Thread to unlock
        ai_path: Path to .ai directory

    Returns:
        Status message
    """
    try:
        from ai_smartness.storage.threads import ThreadStorage

        db_path = ai_path / "db"
        storage = ThreadStorage(db_path / "threads")

        success = storage.unlock(thread_id)

        if success:
            return f"# Thread Unlocked\n\n{thread_id} is now unlocked and can be merged."
        else:
            return f"# Unlock Failed\n\nThread {thread_id} not found or not locked."

    except Exception as e:
        return f"# Unlock Error\n\n{e}"


def parse_virtual_path(path: str) -> Tuple[str, Optional[str], Dict[str, str]]:
    """
    Parse a virtual .ai path into action, target, and params.

    Examples:
        .ai/recall/solana -> ("recall", "solana", {})
        .ai/merge/thread_a/thread_b -> ("merge", "thread_a/thread_b", {})
        .ai/split/thread_x/confirm?titles=A,B&msgs_0=m1 -> ("split", "thread_x/confirm", {"titles": "A,B", ...})
        .ai/unlock/thread_x -> ("unlock", "thread_x", {})

    Args:
        path: Virtual path string

    Returns:
        Tuple of (action, target, params)
    """
    # Remove .ai/ prefix
    if path.startswith(".ai/"):
        path = path[4:]

    # Split query params
    params = {}
    if "?" in path:
        path, query = path.split("?", 1)
        for part in query.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = value

    # Split action and target
    parts = path.split("/", 1)
    action = parts[0]
    target = parts[1] if len(parts) > 1 else None

    return action, target, params


def handle_help(ai_path: Path) -> str:
    """
    Handle help request: .ai/help

    Returns comprehensive agent capabilities documentation.

    Args:
        ai_path: Path to .ai directory

    Returns:
        Help documentation string
    """
    # Get current context info if available
    context_line = ""
    try:
        import json
        heartbeat_path = ai_path / "heartbeat.json"
        if heartbeat_path.exists():
            data = json.loads(heartbeat_path.read_text())
            pct = data.get("context_percent", 0)
            threshold = data.get("compact_threshold", 95)
            if pct > 0:
                context_line = f"\n📊 Contexte actuel: {pct}% utilisé (auto-compact à {threshold}%)\n"
    except Exception:
        pass

    # Get thread stats
    stats_line = ""
    try:
        from ai_smartness.storage.threads import ThreadStorage
        db_path = ai_path / "db"
        storage = ThreadStorage(db_path / "threads")
        stats = storage.get_weight_stats()
        if stats.get("total", 0) > 0:
            stats_line = f"\n📈 Threads: {stats['active_count']} actifs, {stats['suspended_count']} suspendus, {stats['total']} total\n"
    except Exception:
        pass

    return f"""# 🧠 AI SMARTNESS - Agent Help
{context_line}{stats_line}
## Commandes disponibles

### 📖 RECALL - Recherche sémantique dans ta mémoire
```
Read(".ai/recall/<query>")     - Recherche par mot-clé/sujet
Read(".ai/recall/thread_xxx")  - Rappel d'un thread spécifique
```
**Exemples:**
- `.ai/recall/solana` - Tout ce qui concerne Solana
- `.ai/recall/hooks` - Mémoire sur les hooks
- `.ai/recall/authentication` - Travaux sur l'auth

**Résultat:** Threads matchants avec score, topics, résumé, bridges liés

---

### 🔀 MERGE - Fusionner 2 threads (libère du contexte)
```
Read(".ai/merge/<survivor_id>/<absorbed_id>")
```
**Comportement:**
- Le survivor absorbe messages, topics, tags du absorbed
- Messages triés par timestamp
- Weight = max(both) + 0.1 boost
- Le absorbed est archivé avec tag `merged_into:survivor_id`
- Embedding recalculé

**⚠️ Restriction:** Threads avec `split_locked=True` ne peuvent PAS être absorbés

---

### ✂️ SPLIT - Séparer un thread qui a drifté (workflow 2 étapes)

**Étape 1 - Lister les messages:**
```
Read(".ai/split/<thread_id>")
```
→ Retourne la liste des messages avec leurs IDs

**Étape 2 - Confirmer le split:**
```
Read(".ai/split/<id>/confirm?titles=T1,T2&msgs_0=m1,m2&msgs_1=m3,m4&lock=compaction")
```

**Paramètres:**
- `titles` - Titres des nouveaux threads (séparés par virgule)
- `msgs_N` - IDs des messages pour le thread N (0-indexed)
- `lock` - Mode de protection:
  - `compaction` (défaut) - Auto-unlock au prochain compactage
  - `agent_release` - Unlock manuel via `.ai/unlock/`
  - `force` - Jamais d'auto-unlock

**Résultat:** Nouveaux threads créés, tous `split_locked=True`

---

### 🔓 UNLOCK - Déverrouiller un thread split_locked
```
Read(".ai/unlock/<thread_id>")
```
→ Retire la protection split_lock, permet le merge

---

### ❓ HELP - Cette documentation
```
Read(".ai/help")
```

---

## Comportements automatiques

- **Contexte auto-injecté** selon pertinence de ton message
- **Threads persistés** entre sessions
- **Bridges** connectent les sujets liés
- **Auto-compact** à {threshold}% du contexte

## Tips

1. **Libérer du contexte:** Merge des threads similaires ou split pour archiver des sous-sujets
2. **Recall proactif:** Utilise recall avant de travailler sur un sujet déjà abordé
3. **Split tactique:** Quand un thread drift, split pour garder le focus
4. **Lock strategy:** Utilise `force` si tu veux contrôler totalement le lifecycle

---
*AI Smartness v4.3 - Meta-cognition layer for LLM agents*
"""


def handle_virtual_path(path: str, ai_path: Path) -> Optional[str]:
    """
    Handle a virtual .ai/ path and return appropriate content.

    Supported paths:
        .ai/help - Agent capabilities documentation
        .ai/recall/<query> - Memory recall
        .ai/merge/<survivor>/<absorbed> - Merge threads
        .ai/split/<thread_id> - Get split info
        .ai/split/<thread_id>/confirm?... - Execute split
        .ai/unlock/<thread_id> - Unlock thread

    Args:
        path: Virtual path
        ai_path: Path to .ai directory

    Returns:
        Response content, or None if not a recognized path
    """
    action, target, params = parse_virtual_path(path)

    if action == "help":
        return handle_help(ai_path)

    elif action == "recall" and target:
        return handle_recall(target, ai_path)

    elif action == "merge" and target:
        # target is "survivor_id/absorbed_id"
        parts = target.split("/")
        if len(parts) == 2:
            return handle_merge(parts[0], parts[1], ai_path)
        return "# Merge Error\n\nUsage: .ai/merge/<survivor_id>/<absorbed_id>"

    elif action == "split" and target:
        if "/confirm" in target:
            # Split confirmation
            thread_id = target.replace("/confirm", "")
            return handle_split_confirm(thread_id, params, ai_path)
        else:
            # Split info request
            return handle_split_info(target, ai_path)

    elif action == "unlock" and target:
        return handle_unlock(target, ai_path)

    return None
