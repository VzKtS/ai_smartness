"""
Recall handler for AI Smartness v5.0.

Handles active memory recall queries triggered by Read(".ai/recall/<query>").
Searches threads and bridges, formats results for agent consumption.

Features:
- Search by query or thread ID
- Include suspended threads (with score threshold)
- Auto-reactivate suspended threads with high relevance
- Format with Last active timestamp for staleness evaluation
- V5: Focus boost and relevance score integration
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
    threshold = 95  # Default value
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
## MCP Tools disponibles

### 📖 ai_recall(query) - Recherche sémantique dans ta mémoire
```
ai_recall(query="authentication")   # Recherche par mot-clé/sujet
ai_recall(query="thread_xxx")       # Rappel d'un thread spécifique
```
**Exemples:**
- `ai_recall(query="solana")` - Tout ce qui concerne Solana
- `ai_recall(query="hooks")` - Mémoire sur les hooks
- `ai_recall(query="authentication")` - Travaux sur l'auth

**Résultat:** Threads matchants avec score, topics, résumé, bridges liés

---

### 🔀 ai_merge(survivor_id, absorbed_id) - Fusionner 2 threads (libère du contexte)
```
ai_merge(survivor_id="t1", absorbed_id="t2")
```
**Comportement:**
- Le survivor absorbe messages, topics, tags du absorbed
- Messages triés par timestamp
- Weight = max(both) + 0.1 boost
- Le absorbed est archivé avec tag `merged_into:survivor_id`
- Embedding recalculé

**⚠️ Restriction:** Threads avec `split_locked=True` ne peuvent PAS être absorbés

---

### ✂️ ai_split(thread_id, ...) - Séparer un thread qui a drifté (workflow 2 étapes)

**Étape 1 - Lister les messages:**
```
ai_split(thread_id="abc")
```
→ Retourne la liste des messages avec leurs IDs

**Étape 2 - Confirmer le split:**
```
ai_split(thread_id="abc", confirm=True, titles=["T1", "T2"], message_groups=[["m1", "m2"], ["m3", "m4"]])
```

**Paramètres:**
- `titles` - Liste des titres des nouveaux threads
- `message_groups` - Liste de listes d'IDs de messages
- `lock_mode` - Mode de protection:
  - `compaction` (défaut) - Auto-unlock au prochain compactage
  - `agent_release` - Unlock manuel via `ai_unlock()`
  - `force` - Jamais d'auto-unlock

**Résultat:** Nouveaux threads créés, tous `split_locked=True`

---

### 🔓 ai_unlock(thread_id) - Déverrouiller un thread split_locked
```
ai_unlock(thread_id="abc")
```
→ Retire la protection split_lock, permet le merge

---

### ❓ ai_help() - Cette documentation
### 📊 ai_status() - Status mémoire (threads, bridges, contexte)

---

## V5 Hybrid Enhancement Tools

### 💡 ai_suggestions(context?) - Suggestions proactives d'optimisation
```
ai_suggestions()                    # Suggestions générales
ai_suggestions(context="auth")      # Suggestions ciblées
```
**Retourne:**
- `merge_candidates` - Threads similaires à fusionner
- `split_candidates` - Threads avec drift détecté
- `recall_hints` - Sujets à rappeler
- `health` - Métriques santé mémoire

---

### 🗜️ ai_compact(strategy?, dry_run?) - Compaction on-demand
```
ai_compact()                         # Compaction normale
ai_compact(strategy="aggressive")    # Compaction agressive
ai_compact(dry_run=True)            # Preview sans exécuter
```
**Stratégies:**
- `gentle` - Merge >0.95 similarité, archive >30j
- `normal` (défaut) - Merge >0.85, archive >14j
- `aggressive` - Merge >0.75, archive >7j

---

### 🎯 ai_focus(topic, weight?) / ai_unfocus(topic?) - Guide les injections
```
ai_focus(topic="solana", weight=0.9)  # Priorise threads Solana
ai_unfocus(topic="solana")            # Retire focus
ai_unfocus()                          # Clear tout
```
→ Les hooks injecteront en priorité les threads matchant le focus

---

### 📌 ai_pin(content, title?, topics?, weight_boost?) - Capture prioritaire
```
ai_pin(content="Important: ...", title="User Prefs", topics=["config"])
```
→ Crée un thread high-weight qui bypass la cohérence normale

---

### 👍 ai_rate_context(thread_id, useful, reason?) - Feedback qualité
```
ai_rate_context(thread_id="abc", useful=True)
ai_rate_context(thread_id="xyz", useful=False, reason="outdated")
```
→ Ajuste le `relevance_score` pour améliorer les futures injections

---

## V5.1 Full Context Continuity

### 👤 ai_profile(action, key?, value?) - Gestion du profil utilisateur
```
ai_profile(action="view")                           # Voir le profil
ai_profile(action="set_role", key="developer")      # Définir le rôle
ai_profile(action="set_preference", key="language", value="fr")
ai_profile(action="add_rule", key="Toujours vérifier les tests")
ai_profile(action="remove_rule", key="...")
```
**Actions:**
- `view` - Affiche le profil complet
- `set_role` - Définit le rôle (developer/owner/user)
- `set_preference` - Modifie une préférence
- `add_rule` / `remove_rule` - Gère les règles de contexte

**Préférences disponibles:** language, verbosity, emoji_usage, technical_level

---

## Comportements automatiques (V5.1)

- **Session State** - Reprise immédiate du contexte de travail
- **Layered Injection** - 5 couches de contexte par priorité
- **User Profile** - Personnalisation basée sur le rôle et préférences
- **Contexte auto-injecté** selon pertinence + focus + relevance_score
- **Threads persistés** entre sessions
- **Bridges** connectent les sujets liés
- **Auto-compact** à {threshold}% du contexte

## Injection Layers (V5.1)

1. **Session State** - Reprise immédiate (< 1h)
2. **Work Context** - Lien thread ↔ fichiers modifiés
3. **Pinned Content** - Contenu prioritaire
4. **Thread Relevance** - Mémoire thématique
5. **User Profile** - Personnalisation (> 1h)

---

## V5.1.2 Cleanup Tools

### 🧹 ai_cleanup(mode?, dry_run?) - Nettoyer les threads mal nommés
```
ai_cleanup()                        # Mode auto (heuristiques)
ai_cleanup(mode="interactive")      # Mode interactif (analyse par l'agent)
ai_cleanup(dry_run=True)           # Preview sans modifier
```
**Modes:**
- `auto` (défaut) - Corrige automatiquement avec heuristiques
- `interactive` - Retourne la liste pour analyse manuelle par l'agent

---

### ✏️ ai_rename(thread_id, new_title) - Renommer un thread
```
ai_rename(thread_id="thread_xxx", new_title="Mon nouveau titre")
```
→ Utilisé après `ai_cleanup(mode="interactive")` pour corriger les titres

---

## V5.2 Batch Operations & Auto-Optimization

### 📦 ai_merge_batch(operations) - Merge multiple threads at once
```
ai_merge_batch(operations=[
    {{"survivor_id": "t1", "absorbed_id": "t2"}},
    {{"survivor_id": "t3", "absorbed_id": "t4"}}
])
```
→ Plus efficace que plusieurs appels `ai_merge()`

---

### 📦 ai_rename_batch(operations) - Rename multiple threads at once
```
ai_rename_batch(operations=[
    {{"thread_id": "t1", "new_title": "New Title 1"}},
    {{"thread_id": "t2", "new_title": "New Title 2"}}
])
```
→ Plus efficace que plusieurs appels `ai_rename()`

---

### 🔄 Proactive Compression (automatique)
Le daemon surveille la pression mémoire et déclenche automatiquement:
- `> 0.80` → compaction normale
- `> 0.95` → compaction agressive

Configuration dans `config.json`:
```json
{{
  "settings": {{
    "auto_optimization": {{
      "proactive_compact_enabled": true,
      "proactive_compact_threshold": 0.80
    }}
  }}
}}
```

---

## Tips

1. **Libérer du contexte:** `ai_compact()` ou merge des threads similaires
2. **Recall proactif:** `ai_recall()` avant de travailler sur un sujet déjà abordé
3. **Optimisation:** `ai_suggestions()` pour voir les opportunités d'amélioration
4. **Focus temporaire:** `ai_focus()` quand tu travailles sur un sujet précis
5. **Feedback loop:** `ai_rate_context()` pour améliorer les injections futures
6. **Profil:** `ai_profile()` pour personnaliser ton expérience

---
*AI Smartness v6.0.1 - Shared Cognition + Auto-Optimization for LLM agents*
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
