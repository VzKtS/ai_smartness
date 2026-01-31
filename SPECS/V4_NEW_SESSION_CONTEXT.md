# AI Smartness v4.2 - New Session Context

## Problème

Après une interruption (crash, "prompt too long", reload window, nouvelle session), le nouvel agent:
- Ne sait pas qu'AI Smartness existe ni ses capabilities
- Ne sait pas où la session précédente en était
- Reçoit des threads par similarité, pas par récence/pertinence
- Premier message peut ne pas matcher le contexte précédent

## Objectif

Une seule injection concise (~500 chars) sur nouvelle session qui:
1. Informe des capabilities disponibles
2. Indique où on en était
3. Suggère proactivement le recall si pertinent

## Principes de design

1. **Une seule injection** - Pas de pollution multiple
2. **Concis** - ~500 chars max, pas de documentation
3. **Actionnable** - Exemples concrets, pas de théorie
4. **Hot Thread** - Toujours injecter le dernier thread actif
5. **Recall proactif** - Suggérer si le message matche la mémoire

## Mécanisme

### Détection de nouvelle session

Utiliser `session_id` fourni par Claude Code:

```python
def is_new_session(session_id: str, ai_path: Path) -> bool:
    """Check if this is a new session."""
    heartbeat = load_heartbeat(ai_path)
    last_session_id = heartbeat.get("last_session_id")
    return last_session_id is None or session_id != last_session_id
```

### Hot Thread

Le "hot thread" est le dernier thread sur lequel on travaillait, indépendamment de la similarité:

```python
def get_hot_thread(ai_path: Path) -> Optional[dict]:
    """Get the last active thread (hot thread)."""
    heartbeat = load_heartbeat(ai_path)
    last_thread_id = heartbeat.get("last_thread_id")

    if not last_thread_id:
        return None

    thread_path = ai_path / "db" / "threads" / f"{last_thread_id}.json"
    if thread_path.exists():
        return json.loads(thread_path.read_text())

    return None
```

### Recall proactif

Analyser le premier message et suggérer si match:

```python
def suggest_recall(user_message: str, ai_path: Path) -> Optional[str]:
    """Suggest recall if user message matches memory."""
    from ai_smartness.intelligence.memory_retriever import MemoryRetriever

    # Quick keyword extraction (simple)
    words = set(user_message.lower().split())

    # Check against thread topics
    threads_dir = ai_path / "db" / "threads"
    matching_topics = []

    for tf in threads_dir.glob("*.json"):
        try:
            thread = json.loads(tf.read_text())
            topics = [t.lower() for t in thread.get("topics", [])]
            matches = words & set(topics)
            if matches:
                matching_topics.extend(matches)
        except:
            pass

    if matching_topics:
        # Return most common match
        topic = max(set(matching_topics), key=matching_topics.count)
        return topic

    return None
```

## Format d'injection

### Structure unifiée

```
🧠 AI SMARTNESS

Capabilities:
• Read(".ai/recall/<query>") - Rechercher ta mémoire
• Contexte auto-injecté selon pertinence

Session: Nouvelle (2h 15min depuis dernière interaction)
Hot thread: "V4.0 Recall Actif Implementation"
Topics: ai_smartness, recall, hooks
Résumé: Implémentation du recall via pretool.py

💡 Ton message mentionne "recall" - mémoire disponible:
→ Read(".ai/recall/recall")
```

### Taille cible

| Section | Chars |
|---------|-------|
| Header + Capabilities | ~150 |
| Session info | ~100 |
| Hot thread context | ~200 |
| Recall suggestion | ~50 |
| **Total** | **~500** |

## Implémentation

### Dans `hooks/inject.py`

```python
def get_new_session_context(
    session_id: str,
    user_message: str,
    ai_path: Path
) -> Optional[str]:
    """
    Get unified new session context.

    Args:
        session_id: Current session ID from Claude Code
        user_message: The user's first message
        ai_path: Path to .ai directory

    Returns:
        New session context string or None if same session
    """
    if not is_new_session(session_id, ai_path):
        return None

    lines = ["🧠 AI SMARTNESS", ""]

    # 1. Capabilities (toujours)
    lines.extend([
        "Capabilities:",
        "• Read(\".ai/recall/<query>\") - Rechercher ta mémoire",
        "• Contexte auto-injecté selon pertinence",
        ""
    ])

    # 2. Session info
    time_elapsed = get_time_since_last(ai_path)
    if time_elapsed:
        elapsed_str = format_elapsed(time_elapsed)
        lines.append(f"Session: Nouvelle ({elapsed_str} depuis dernière interaction)")
    else:
        lines.append("Session: Première utilisation")

    # 3. Hot thread (si existe)
    hot_thread = get_hot_thread(ai_path)
    if hot_thread:
        title = hot_thread.get("title", "Sans titre")[:50]
        topics = ", ".join(hot_thread.get("topics", [])[:4])
        summary = hot_thread.get("summary", "")[:100]

        lines.append(f"Hot thread: \"{title}\"")
        if topics:
            lines.append(f"Topics: {topics}")
        if summary:
            lines.append(f"Résumé: {summary}")

    # 4. Check for recent synthesis (from PreCompact)
    synthesis = get_latest_synthesis(ai_path, max_age_hours=2)
    if synthesis and not hot_thread:
        # Use synthesis if no hot thread
        lines.append(f"Dernier contexte: {synthesis.get('summary', '')[:150]}")

    lines.append("")

    # 5. Recall proactif (si match)
    if user_message:
        suggested_topic = suggest_recall(user_message, ai_path)
        if suggested_topic:
            lines.extend([
                f"💡 Ton message mentionne \"{suggested_topic}\" - mémoire disponible:",
                f"→ Read(\".ai/recall/{suggested_topic}\")"
            ])

    return "\n".join(lines)


def get_latest_synthesis(ai_path: Path, max_age_hours: int = 2) -> Optional[dict]:
    """Get latest synthesis if recent enough."""
    synthesis_dir = ai_path / "db" / "synthesis"
    if not synthesis_dir.exists():
        return None

    # Get most recent synthesis file
    synthesis_files = sorted(synthesis_dir.glob("synthesis_*.json"), reverse=True)
    if not synthesis_files:
        return None

    latest = synthesis_files[0]
    try:
        data = json.loads(latest.read_text())
        generated_at = data.get("generated_at")
        if generated_at:
            age = datetime.now() - datetime.fromisoformat(generated_at)
            if age.total_seconds() < max_age_hours * 3600:
                return data
    except:
        pass

    return None


def format_elapsed(delta: timedelta) -> str:
    """Format timedelta to human readable."""
    total_seconds = delta.total_seconds()

    if total_seconds < 60:
        return "quelques secondes"
    elif total_seconds < 3600:
        minutes = int(total_seconds // 60)
        return f"{minutes}min"
    elif total_seconds < 86400:
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}h {minutes}min"
    else:
        days = int(total_seconds // 86400)
        return f"{days} jour(s)"
```

### Modification heartbeat.py

Ajouter tracking session_id et thread info:

```python
def record_interaction(
    ai_path: Path,
    session_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    thread_title: Optional[str] = None
) -> None:
    """
    Record that an interaction occurred.

    Args:
        ai_path: Path to .ai directory
        session_id: Current session ID from Claude Code
        thread_id: Current thread ID (hot thread)
        thread_title: Current thread title
    """
    heartbeat = load_heartbeat(ai_path)
    heartbeat["last_interaction_at"] = datetime.now().isoformat()
    heartbeat["last_interaction_beat"] = heartbeat.get("beat", 0)

    if session_id:
        heartbeat["last_session_id"] = session_id
    if thread_id:
        heartbeat["last_thread_id"] = thread_id
    if thread_title:
        heartbeat["last_thread_title"] = thread_title

    save_heartbeat(ai_path, heartbeat)


def is_new_session(session_id: str, ai_path: Path) -> bool:
    """Check if this is a new session."""
    heartbeat = load_heartbeat(ai_path)
    last_session_id = heartbeat.get("last_session_id")
    return last_session_id is None or session_id != last_session_id


def get_time_since_last(ai_path: Path) -> Optional[timedelta]:
    """Get time since last interaction."""
    heartbeat = load_heartbeat(ai_path)
    last_at = heartbeat.get("last_interaction_at")
    if not last_at:
        return None
    try:
        return datetime.now() - datetime.fromisoformat(last_at)
    except ValueError:
        return None
```

## Intégration dans inject.py main()

```python
def main():
    hook_input = get_hook_input_from_stdin()
    session_id = hook_input.get("session_id", "")
    user_message = hook_input.get("user_message", "")

    injections = []

    # 1. New Session Context (unified onboarding + recovery + recall suggestion)
    new_session_ctx = get_new_session_context(session_id, user_message, ai_path)
    if new_session_ctx:
        injections.append(f"<system-reminder>\n{new_session_ctx}\n</system-reminder>")

    # 2. Regular thread injection by similarity (always)
    thread_context = get_thread_context(user_message, ai_path)
    if thread_context:
        injections.append(f"<system-reminder>\n{thread_context}\n</system-reminder>")

    # 3. Update heartbeat
    record_interaction(ai_path, session_id=session_id)

    # Output
    if injections:
        print(json.dumps({"prefix_messages": injections}))
```

## Exemples d'injection

### Première session (fresh install)

```
🧠 AI SMARTNESS

Capabilities:
• Read(".ai/recall/<query>") - Rechercher ta mémoire
• Contexte auto-injecté selon pertinence

Session: Première utilisation
```

### Nouvelle session après travail

```
🧠 AI SMARTNESS

Capabilities:
• Read(".ai/recall/<query>") - Rechercher ta mémoire
• Contexte auto-injecté selon pertinence

Session: Nouvelle (2h 15min depuis dernière interaction)
Hot thread: "V4.0 Recall Actif Implementation"
Topics: ai_smartness, recall, hooks, pretool
Résumé: Implémentation du système de recall actif via Read(".ai/recall/...")
```

### Nouvelle session avec recall suggéré

```
🧠 AI SMARTNESS

Capabilities:
• Read(".ai/recall/<query>") - Rechercher ta mémoire
• Contexte auto-injecté selon pertinence

Session: Nouvelle (45min depuis dernière interaction)
Hot thread: "Solana Token Implementation"
Topics: solana, rust, anchor
Résumé: Création d'un token SPL avec Anchor framework

💡 Ton message mentionne "solana" - mémoire disponible:
→ Read(".ai/recall/solana")
```

## Tracking dans heartbeat.json

```json
{
  "beat": 847,
  "started_at": "2026-01-15T08:00:00",
  "last_beat_at": "2026-01-31T14:30:00",
  "last_interaction_at": "2026-01-31T14:25:00",
  "last_interaction_beat": 845,
  "last_session_id": "abc123-def456-ghi789",
  "last_thread_id": "thread_20260131_142000_abc123",
  "last_thread_title": "V4.0 Recall Actif Implementation"
}
```

## Fichiers à modifier

| Fichier | Modification |
|---------|-------------|
| `storage/heartbeat.py` | Ajouter `session_id`, `thread_id`, `thread_title` params |
| `hooks/inject.py` | Ajouter `get_new_session_context()`, intégrer dans main() |
| `hooks/capture.py` | Appeler `record_interaction()` avec thread info |

## Tests

1. **Fresh install**: Premier message → voit capabilities seulement
2. **Même session**: Messages suivants → pas de new session context
3. **Nouvelle session**: Après reload → voit hot thread + temps écoulé
4. **Recall match**: Message avec keyword connu → suggestion recall
5. **Synthesis fallback**: Si hot thread absent mais synthesis récente → utilise synthesis

## Relation avec autres features

| Feature | Quand | Contenu |
|---------|-------|---------|
| New Session Context | Nouvelle session | Capabilities + Hot thread + Recall suggestion |
| Thread injection | Toujours | Threads par similarité |
| PreCompact synthesis | 95% contexte | Sauvegardé, peut être réutilisé |
| Recall actif | Agent request | Résultats mémoire |

## Version

- **v4.2.0**: New Session Context (unifie Onboarding + Recovery + Recall proactif)

## Specs remplacées

Ce document remplace:
- `V4_AGENT_ONBOARDING.md`
- `V4_SESSION_RECOVERY.md`
