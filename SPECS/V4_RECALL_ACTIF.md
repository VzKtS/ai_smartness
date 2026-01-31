# AI Smartness v4.0 - Recall Actif

## Objectif

Permettre à l'agent de requêter activement la mémoire via un Read virtuel, recevant le résultat **dans le même tour**.

## Mécanisme

### Pattern d'appel
```
Read(".ai/recall/<query>")
```

Exemples:
- `Read(".ai/recall/solana validators")`
- `Read(".ai/recall/consensus mechanism")`
- `Read(".ai/recall/thread_20250130_123456")`  # ID spécifique

### Interception

**Hook**: `PreToolUse` (capture.py)

**Détection**:
```python
RECALL_PATTERN = re.compile(r'^\.ai/recall/(.+)$')
```

**Flow**:
```
Agent appelle Read(".ai/recall/solana validators")
    ↓
PreToolUse hook reçoit {"tool": "Read", "input": {"file_path": ".ai/recall/solana validators"}}
    ↓
Pattern matche → extraire query "solana validators"
    ↓
MemoryRetriever.search(query, include_suspended=True)
    ↓
Formater résultat comme contenu de fichier virtuel
    ↓
Retourner {"result": "<formatted_memory>"} au lieu de lire le fichier
    ↓
Agent reçoit le contexte mémoire immédiatement
```

### Format de réponse

```
# Memory Recall: solana validators
Query executed at: 2026-01-31 10:30:00

## Matching Threads (3 found)

### [ACTIVE] Solana Validator Setup (thread_20250128...)
Weight: 0.85 | Topics: solana, validator, devnet
Summary: Configuration et déploiement d'un validateur Solana sur devnet...
Last active: 2 days ago

### [SUSPENDED] Consensus Mechanisms (thread_20250120...)
Weight: 0.08 | Topics: consensus, proof-of-stake, solana
Summary: Comparaison des mécanismes de consensus blockchain...
Last active: 11 days ago
→ Reactivated by this recall

### [ACTIVE] Network Monitoring (thread_20250129...)
Weight: 0.72 | Topics: monitoring, solana, metrics
Summary: Mise en place du monitoring pour infrastructure Solana...
Last active: 1 day ago

## Related Bridges (2 found)

- Validator Setup → Network Monitoring (EXTENDS, weight: 0.65)
- Consensus Mechanisms → Validator Setup (DEPENDS, weight: 0.45)
```

### Note sur le contexte temporel

Le champ `Last active: X days ago` dans les résultats de recall sert à évaluer la **fraîcheur de l'information**, pas la perception temporelle de l'agent.

**Distinction importante:**
- **Heartbeat/beats** (v4.x) → Perception du temps qui passe pour l'agent entre les messages (abstrait, "temps système")
- **Last active** → Indicateur de staleness pour l'information rappelée

Ces deux concepts sont complémentaires:
- `beat: 847, since_last: 12` → L'agent sait qu'il s'est passé du temps depuis la dernière interaction
- `Last active: 11 days ago` → L'agent sait que cette mémoire est potentiellement obsolète

C'est comme la différence entre "savoir quelle heure il est" et "savoir qu'un document a été modifié il y a 2 semaines".

**Recommandation agent**: Utiliser `Last active` pour pondérer la fiabilité de l'information rappelée. Un thread actif récemment a plus de chances d'être à jour qu'un thread suspendu depuis 11 jours.

### Réactivation automatique

Si un thread suspendu matche avec score > 0.5:
1. Réactiver le thread (status → ACTIVE)
2. Boost weight (+0.1)
3. Logger la réactivation
4. Inclure mention "→ Reactivated by this recall" dans le résultat

## Implémentation

### Fichiers à modifier

1. **hooks/capture.py** - Ajouter détection recall dans PreToolUse
2. **intelligence/memory_retriever.py** - Ajouter `search()` method avec include_suspended
3. **cli/commands/search.py** - Réutiliser la logique existante

### Nouveau fichier

`hooks/recall.py` - Logique de recall actif:
```python
def handle_recall(query: str, ai_path: Path) -> str:
    """
    Handle a recall query and return formatted memory context.

    Args:
        query: Search query or thread ID
        ai_path: Path to .ai directory

    Returns:
        Formatted memory context string
    """
```

### Modifications capture.py

```python
# Dans la fonction main() de PreToolUse

def main():
    # ... existing code ...

    # Check for recall pattern
    if tool == "Read":
        file_path = input_data.get("file_path", "")
        recall_match = RECALL_PATTERN.match(file_path)
        if recall_match:
            query = recall_match.group(1)
            result = handle_recall(query, ai_path)
            # Return intercepted result
            print(json.dumps({"result": result}))
            return

    # ... normal capture flow ...
```

## Anti-loop

Le recall utilise le même guard que les autres hooks:
```python
if os.environ.get("AI_SMARTNESS_HOOK_RUNNING"):
    # Pass through, don't recurse
    return
```

## CLI Équivalent

Pour cohérence, ajouter aussi:
```bash
ai recall "solana validators"
```

Qui fait la même chose que `Read(".ai/recall/solana validators")` mais en CLI.

## Tests

1. **Test basique**: `Read(".ai/recall/test query")` retourne du contexte
2. **Test réactivation**: Query qui matche un thread suspendu le réactive
3. **Test ID direct**: `Read(".ai/recall/thread_xxx")` retourne le thread spécifique
4. **Test no-match**: Query sans résultat retourne message approprié
5. **Test anti-loop**: Pas de récursion infinie

## Métriques

Logger dans `.ai/recall.log`:
```
[2026-01-31 10:30:00] RECALL "solana validators" → 3 threads, 2 bridges, 1 reactivated
```

## Version

- **v4.0.0**: Recall Actif initial
- Bump minor car nouvelle feature majeure
