# AI Smartness - Roadmap Architecture Neuronale

## Vision

Transformer AI Smartness en véritable **réseau neuronal mémoriel** :
- **Threads** = Neurones (persistants, peuvent dormir)
- **ThinkBridges** = Synapses (dynamiques, peuvent mourir)
- **Parent-Child** = Structure axonale (hiérarchie)
- **Gossip** = Plasticité synaptique (création/renforcement)
- **Pruning** = Mort synaptique (oubli actif)

---

## Phase 15: Universal Coherence Chain ✅ DONE (v2.7.0)

### Objectif
~~Étendre le coherence-based child linking à tous les outils "context-setting".~~

**Évolution**: Tous les tools sont maintenant "context-setting". Le coherence check devient le filtre naturel.

### Changements Implémentés

**1. Suppression de CONTEXT_TOOLS**

```python
# processor.py - AVANT
CONTEXT_TOOLS = {"Glob", "Grep"}
if tool in self.CONTEXT_TOOLS: ...

# processor.py - APRÈS
# Plus de filtre - tous les tools créent pending_context
# et vérifient la cohérence avec le précédent
```

**2. Flow universel**

```
Tool N → Thread A (set pending_context)
    ↓
Tool N+1 → coherence check avec A
    ↓
    ├─ >0.6 → Thread B child of A (set pending_context = B)
    ├─ 0.3-0.6 → Thread B orphan (set pending_context = B)
    └─ <0.3 → SKIP (keep pending_context = A pour next)
```

**3. Chaîne naturelle**

```
Prompt → Read → Grep → Write → Bash → ...
   ↓        ↓       ↓       ↓       ↓
 root  → child → child → orphan → child
        (0.8)   (0.7)   (0.4)    (0.9)
```

### Critères de succès
- [x] Tous les tools créent pending_context
- [x] Coherence check systématique avant chaque thread
- [x] Hierarchie parent-child basée sur cohérence sémantique

---

## Phase 16: Confidence Tuning (Optionnel)

### Objectif
Affiner les seuils de coherence dynamiquement.

### Options

**Option A: Embeddings purs (sentence-transformers)**
- Rapide, pas d'appel LLM supplémentaire
- Moins précis sur relations subtiles
- Déjà disponible

**Option B: LLM Haiku (actuel)**
- Plus précis
- Coût ~$0.00025/appel
- Latence 1-2s

**Option C: Hybride**
```python
# Embedding similarity d'abord
embed_sim = embeddings.similarity(context, content)

if embed_sim > 0.7:
    # Très similaire → child direct (skip LLM)
    return "child"
elif embed_sim < 0.2:
    # Très différent → orphan direct (skip LLM)
    return "orphan"
else:
    # Zone grise → LLM décide
    return llm_coherence_check(context, content)
```

### Décision
À évaluer après Phase 15 selon :
- Performance observée
- Taux de faux positifs/négatifs
- Coût LLM accumulé

---

## Phase 17: Bridge Weight Decay ✅ DONE (v2.8.0)

### Objectif
Implémenter le "pruning synaptique" - les bridges inutilisés meurent.

### Changements Implémentés

**1. ThinkBridge model** (`models/bridge.py`)
- Ajout `weight: float` (initialisé depuis confidence)
- Ajout constantes: `HALF_LIFE_DAYS = 3.0`, `DEATH_THRESHOLD = 0.05`, `USE_BOOST = 0.1`
- Méthode `decay()` avec demi-vie exponentielle
- Méthode `is_alive()` pour vérifier survie
- `record_use()` booste le weight (renforcement Hebbien)

**2. BridgeStorage** (`storage/bridges.py`)
- `prune_dead_bridges()` - applique decay et supprime les morts
- `get_alive()` - retourne seulement les bridges vivants
- `get_weight_stats()` - statistiques de poids

**3. GossipPropagator** (`intelligence/gossip.py`)
- `prune_dead_bridges()` - wrapper pour storage
- `get_bridge_health()` - métriques réseau
- `weaken_unused_bridges()` - deprecated, redirige vers prune

**4. CLI** (`cli/commands/bridges.py`, `cli/main.py`)
- `--show-weight` / `-w` - affiche colonne weight
- `--prune` - applique decay et supprime les bridges morts

### Modèle ThinkBridge étendu

```python
@dataclass
class ThinkBridge:
    # ... existant ...

    # Nouveau: métriques de vie
    weight: float = 1.0           # Commence à 1.0
    created_at: datetime
    last_used: Optional[datetime] = None
    use_count: int = 0

    # Constantes de decay
    HALF_LIFE_DAYS: int = 7       # Demi-vie sans usage
    DEATH_THRESHOLD: float = 0.05 # Seuil de mort

    def record_use(self):
        """Renforcement Hebbien - usage = renforcement."""
        self.last_used = datetime.now()
        self.use_count += 1
        # Bonus de renforcement (cap à 1.0)
        self.weight = min(1.0, self.weight + 0.1)

    def decay(self) -> bool:
        """
        Applique le decay temporel.
        Returns True si le bridge doit mourir.
        """
        if self.last_used is None:
            reference = self.created_at
        else:
            reference = self.last_used

        hours_unused = (datetime.now() - reference).total_seconds() / 3600
        days_unused = hours_unused / 24

        # Decay exponentiel (demi-vie)
        self.weight *= 0.5 ** (days_unused / self.HALF_LIFE_DAYS)

        return self.weight < self.DEATH_THRESHOLD

    def is_alive(self) -> bool:
        return self.weight >= self.DEATH_THRESHOLD
```

### Quand appliquer le decay

**Option A: Lazy (recommandé)**
- Calculer decay uniquement quand bridge est accédé
- Pas de background job
- Simple, efficace

**Option B: Periodic**
- Job périodique (ex: toutes les heures)
- Nettoie proactivement
- Plus complexe

### Quand "utiliser" un bridge

Un bridge est "utilisé" quand :
1. Il est traversé pendant memory retrieval
2. Il est affiché à l'utilisateur (injection context)
3. Il connecte deux threads actifs simultanément

### Storage

```python
# BridgeStorage
def prune_dead_bridges(self) -> int:
    """Supprime les bridges morts. Retourne le nombre supprimé."""
    all_bridges = self.get_all()
    dead_count = 0

    for bridge in all_bridges:
        if bridge.decay():  # Applique decay et check mort
            self.delete(bridge.id)
            dead_count += 1
        else:
            self.save(bridge)  # Sauvegarde le nouveau poids

    return dead_count
```

### CLI

```bash
ai bridges --show-weight     # Afficher les poids
ai bridges --prune           # Forcer le pruning
ai health                    # Inclure stats bridges (alive/dead ratio)
```

---

## Phase 18: Thread Decay & Mode Management ✅ DONE (v2.9.0)

### Objectif
Implémenter le decay temporel pour les threads et la gestion dynamique des modes.

### Changements Implémentés

**1. Thread model** (`models/thread.py`)
- Ajout constantes: `HALF_LIFE_DAYS = 7.0`, `SUSPEND_THRESHOLD = 0.1`, `USE_BOOST = 0.1`
- Ajout `MODE_QUOTAS = {light: 15, normal: 50, heavy: 100, max: 200}`
- Méthode `decay()` - applique decay, retourne True si suspension nécessaire
- Méthode `should_suspend()` - vérifie si poids < seuil
- Méthode `boost_weight()` - renforcement Hebbien

**2. ThreadStorage** (`storage/threads.py`)
- `prune_threads(mode_quota)` - applique decay + suspend + enforce quota
- `get_weight_stats()` - statistiques de poids
- `enforce_quota(quota)` - suspend les threads en excès

**3. ThreadManager** (`intelligence/thread_manager.py`)
- `get_current_mode()` - lit le mode depuis config
- `get_mode_quota(mode)` - retourne quota pour un mode
- `set_mode(mode)` - change le mode, suspend si nécessaire
- `prune_threads()` - wrapper avec stats
- `get_mode_status()` - status complet

**4. CLI**
- `ai mode status` - affiche mode actuel et stats
- `ai mode light|normal|heavy|max` - change le mode
- `ai threads --prune` - applique decay et suspend
- `ai threads --show-weight` - affiche indicateurs de poids

### Flow
```
ACTIVE ←→ SUSPENDED
   ↓           ↓
(decay)    (reactivation si match > 0.5)
```

### Différences vs Bridges
| Aspect | Bridges | Threads |
|--------|---------|---------|
| Demi-vie | 3 jours | 7 jours |
| Action | Suppression | Suspension |
| Quota | Non | Oui (par mode) |

---

## Phase 19: Gossip Refinement

### Objectif
Adapter la création de bridges au nouveau système.

### Changements

**1. Poids initial basé sur confidence**
```python
def create_bridge(source, target, confidence):
    bridge = ThinkBridge.create(source.id, target.id)
    bridge.weight = confidence  # Pas 1.0, mais la confidence réelle
    bridge.confidence = confidence
```

**2. Parent-child bridges spéciaux**
```python
# Les bridges CHILD_OF ne devraient pas mourir tant que les threads existent
if bridge.relation_type == BridgeType.CHILD_OF:
    bridge.DEATH_THRESHOLD = 0.01  # Très résistant
```

**3. Propagation limitée**
```python
# Ne pas propager depuis des bridges faibles
if source_bridge.weight < 0.3:
    return  # Skip propagation
```

---

## Métriques de Succès Global

| Métrique | Cible | Mesure |
|----------|-------|--------|
| Hiérarchie depth | 2-4 niveaux | Moyenne profondeur parent-child |
| Bridge survival rate | 30-50% | Bridges > 7 jours / total créés |
| False positive rate | < 10% | Bridges morts avant 1er usage |
| Memory retrieval quality | Subjectif | Pertinence contexte injecté |

---

## Ordre d'Implémentation

```
Phase 15: Extended Context Tools
    ↓ (tester, valider)
Phase 16: Confidence Tuning (si nécessaire)
    ↓ (tester, valider)
Phase 17: Bridge Weight Decay
    ↓ (tester, valider)
Phase 18: Gossip Refinement
    ↓
🧠 Réseau Neuronal Mémoriel Complet
```

---

## Notes Techniques

### Backwards Compatibility
- Les bridges existants sans `weight` → default 0.5
- Les bridges existants sans `last_used` → utiliser `created_at`

### Performance
- Decay est O(1) par bridge
- Pruning peut être lazy ou batché
- Pas d'impact sur latence capture/inject

### Observabilité
- Log chaque mort de bridge
- Métriques dans `ai health`
- Export possible pour analyse
