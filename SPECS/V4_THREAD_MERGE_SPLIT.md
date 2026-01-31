# V4.3 - Thread Merge & Split

## Objectif

Permettre à l'agent de fusionner ou diviser des threads pour maintenir une organisation cohérente de la mémoire.

---

## 1. MERGE THREADS

### Use Case
- L'agent détecte que deux threads traitent du même sujet
- L'utilisateur demande explicitement de fusionner deux threads
- Deux threads ont un bridge fort entre eux (même thématique)

### Comportement

```
Thread A (survivor) + Thread B (absorbed) → Thread A (merged)
```

**Thread survivor (A) reçoit:**
- Messages de B ajoutés à A (triés par timestamp)
- Topics/tags de B fusionnés (union)
- Summary concaténé ou régénéré
- Weight = max(A.weight, B.weight) + 0.1 boost
- Embedding recalculé

**Thread absorbed (B):**
- Status → ARCHIVED
- Tag ajouté: `merged_into:{A.id}`
- Conservé pour traçabilité (jamais supprimé)

**Bridges:**
- Bridges pointant vers B → redirigés vers A
- Bridges sortant de B → dupliqués depuis A
- Bridge A↔B → supprimé (auto-référence)

### API

```python
# storage/threads.py
def merge(self, survivor_id: str, absorbed_id: str) -> Thread:
    """Merge two threads. Returns the merged survivor thread."""
```

### Invocation Agent

L'agent peut demander un merge via:
```
Read(".ai/merge/thread_xxx/thread_yyy")
```

Ou via commande CLI:
```bash
ais threads merge thread_xxx thread_yyy
```

---

## 2. SPLIT THREAD

### Use Case
- Un thread a drifté vers plusieurs sujets distincts
- L'agent détecte une bifurcation thématique
- L'agent veut libérer de l'espace contexte pour raisonnement profond

### Comportement

```
Thread A → Thread A (parent) + Thread B, C... (children)
```

**Thread parent (A):**
- Conserve les messages du sujet principal
- `child_ids` mis à jour avec les nouveaux threads
- Weight conservé

**Threads enfants (B, C...):**
- `origin_type = SPLIT`
- `parent_id = A.id`
- `split_locked = True` (OBLIGATOIRE - voir section 2.1)
- `split_locked_until = "compaction"` (défaut)
- Messages assignés selon leur sujet
- Weight = parent.weight * 0.8 (hérite mais réduit)
- Nouveaux embeddings calculés

**Bridges:**
- Bridges du parent restent sur le parent
- Nouveaux bridges créés entre parent et enfants
- Les bridges externes peuvent être dupliqués si pertinent

### 2.1 Split Lock (Protection anti-merge)

Quand l'agent splitte, c'est tactique (libérer contexte). Le système NE DOIT PAS re-merger automatiquement.

**Nouveaux champs Thread:**
```python
split_locked: bool = False
split_locked_until: Optional[str] = None  # "compaction" | "agent_release" | "force"
```

**Valeurs de split_locked_until:**

| Valeur | Comportement |
|--------|--------------|
| `compaction` | Auto-unlock au prochain compactage (défaut) |
| `agent_release` | Unlock quand agent appelle `.ai/unlock/thread_xxx` |
| `force` | Jamais d'auto-unlock, seul l'agent peut merger |

**Règle:** Un thread avec `split_locked=True` est IGNORÉ par tout mécanisme d'auto-merge.

### 2.2 Workflow Interactif (Option D)

**Étape 1 - Agent demande les messages:**
```
Read(".ai/split/thread_xxx")
```

**Réponse:**
```
Thread: thread_xxx "Implémentation V4"
Messages (12):
- msg_001 [user] "Travaillons sur les hooks..."
- msg_002 [assistant] "Je vais implémenter..."
- msg_003 [user] "Passons à Solana maintenant..."
- msg_004 [assistant] "Pour Solana, il faut..."
...

Pour splitter, appelez:
Read(".ai/split/thread_xxx/confirm?titles=Titre1,Titre2&msgs_0=msg_001,msg_002&msgs_1=msg_003,msg_004&lock=compaction")
```

**Étape 2 - Agent confirme le split:**
```
Read(".ai/split/thread_xxx/confirm?titles=Hooks V4,Solana&msgs_0=msg_001,msg_002&msgs_1=msg_003,msg_004&lock=compaction")
```

**Paramètres:**
- `titles`: Titres des nouveaux threads (séparés par virgule)
- `msgs_N`: Messages pour le thread N
- `lock`: Mode de lock (`compaction`, `agent_release`, `force`)

### 2.3 Unlock

```
Read(".ai/unlock/thread_xxx")
```

Retire le `split_locked` pour permettre un futur merge.

### API

```python
# storage/threads.py
def split(
    self,
    thread_id: str,
    split_config: List[dict],
    lock_until: str = "compaction"
) -> List[Thread]:
    """Split a thread. All new threads are split_locked."""

def unlock(self, thread_id: str) -> bool:
    """Remove split_lock from a thread."""
```

### CLI
```bash
ais threads split thread_xxx --interactive
ais threads unlock thread_xxx
```

---

## 3. Injection Capabilities

Ajouter dans le new session context:

```
• Merge threads: Read(".ai/merge/thread_a/thread_b")
• Split thread: Read(".ai/split/thread_id")
```

---

## 4. Implémentation

### Fichiers à modifier

1. **src/ai_smartness/storage/threads.py**
   - `merge(survivor_id, absorbed_id) -> Thread`
   - `split(thread_id, split_config) -> List[Thread]`

2. **src/ai_smartness/hooks/recall.py**
   - Handler pour `.ai/merge/...`
   - Handler pour `.ai/split/...`

3. **src/ai_smartness/cli/commands/threads.py**
   - Commande `ais threads merge`
   - Commande `ais threads split`

4. **src/ai_smartness/hooks/inject.py**
   - Ajouter capabilities merge/split

### Ordre d'implémentation

1. Thread model: ajouter `split_locked`, `split_locked_until`
2. ThreadStorage.merge()
3. ThreadStorage.split() avec lock obligatoire
4. ThreadStorage.unlock()
5. Recall handlers (.ai/merge, .ai/split, .ai/unlock)
6. Hook compact: auto-unlock des threads split_locked_until="compaction"
7. CLI commands
8. Update capabilities injection

---

## 5. Décisions prises

1. **Auto-merge**: NON - l'agent merge quand il veut libérer du contexte, pas automatique
2. **Split workflow**: Option D - Interactif en 2 étapes (list messages → confirm)
3. **Split lock**: OBLIGATOIRE - tout split est locked par défaut
4. **Embeddings**: Recalcul IMMÉDIAT (sentence-transformer local, pas de latence)
