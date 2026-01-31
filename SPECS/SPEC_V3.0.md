# AI Smartness v3.0 - Spécification Technique Complète

## Meta

- **Version**: 3.0.0
- **Date**: 2026-01-31
- **Auteur**: Claude (Opus 4.5) + User
- **Status**: Implemented
- **Changelog**:
  - v2.7.0: Universal Coherence Chain (Phase 15)
  - v2.8.0: Bridge Weight Decay (Phase 17)
  - v2.9.0: Thread Decay & Mode Management (Phase 18)
  - v2.9.1: Weight system alignment (FORK inherits, boost_weight unified)
  - v3.0.0: CLI in Prompt + Daemon auto-pruning timer (Phase 19)

---

## 1. Vision & Architecture

### 1.1 Objectif

AI Smartness v2 est une **couche de méta-cognition** pour agents LLM qui fournit :
- **Mémoire persistante** : Reprendre un projet après des semaines comme si l'utilisateur était parti boire un café
- **Cohérence sémantique** : Naviguer dans des projets complexes sans drift ni hallucinations
- **Relations automatiques** : Découverte et propagation de liens entre sujets (gossip)
- **Garde-fous comportementaux** : Règles injectées pour guider l'agent

### 1.2 Métaphore Neuronale

| Concept | Analogie | Rôle |
|---------|----------|------|
| **Thread** | Neurone | Flux de travail (sujet/topic) |
| **ThinkBridge** | Synapse | Connexion sémantique entre threads |
| **Embedding** | Signal électrique | Représentation vectorielle pour similarité |
| **Gossip** | Plasticité synaptique | Propagation automatique des connexions |
| **GuardCode** | Inhibiteur | Règles comportementales injectées |
| **Decay** | Atrophie synaptique | Oubli naturel par non-usage |
| **Pruning** | Mort neuronale | Suppression bridges morts, suspension threads |

### 1.3 Architecture Système

```
┌─────────────────────────────────────────────────────────────┐
│                     CLAUDE CODE                              │
├─────────────────────────────────────────────────────────────┤
│  UserPromptSubmit    PostToolUse         PreCompact         │
│        │                 │                   │               │
│        ▼                 ▼                   ▼               │
│  ┌──────────┐      ┌──────────┐       ┌──────────┐         │
│  │ inject.py│      │capture.py│       │compact.py│         │
│  └────┬─────┘      └────┬─────┘       └────┬─────┘         │
│       │                 │                   │               │
│       └────────────┬────┴───────────────────┘               │
│                    ▼                                        │
│         ┌─────────────────────┐                            │
│         │  Daemon (processor) │ ◄── Unix Socket            │
│         │  ├─ ThreadManager   │                            │
│         │  ├─ GossipPropagator│                            │
│         │  ├─ LLMExtractor    │                            │
│         │  └─ EmbeddingManager│                            │
│         └──────────┬──────────┘                            │
│                    ▼                                        │
│         ┌─────────────────────┐                            │
│         │   StorageManager    │                            │
│         │   ├─ ThreadStorage  │                            │
│         │   └─ BridgeStorage  │                            │
│         └─────────────────────┘                            │
│                    │                                        │
│                    ▼                                        │
│              .ai/db/*.json                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Modèles de Données

### 2.1 Thread

Le Thread est l'entité centrale - un **flux de travail** (pas une session temporelle).

```python
@dataclass
class Thread:
    id: str                          # "thread_YYYYMMdd_HHMMSS_hex"
    title: str                       # Titre sémantique (5-10 mots, pas de verbes d'action)
    status: ThreadStatus             # ACTIVE | SUSPENDED | ARCHIVED

    # Contenu
    messages: List[Message]          # Historique complet
    summary: str                     # Résumé LLM
    topics: List[str]                # Concepts clés extraits

    # Origine et évolution
    origin_type: OriginType          # PROMPT | FILE_READ | TASK | FETCH | SPLIT | REACTIVATION
    drift_history: List[str]         # Trace des changements de focus

    # Relations parent/enfant
    parent_id: Optional[str]         # Thread parent (si FORK/SPLIT)
    child_ids: List[str]             # Threads enfants

    # Pondération (calculée automatiquement)
    weight: float                    # 0.0-1.0, décroit avec le temps
    last_active: datetime
    activation_count: int

    # Embeddings
    embedding: Optional[List[float]] # Vecteur 384-dim (sentence-transformers)

    # Constantes de decay (class-level)
    HALF_LIFE_DAYS: float = 7.0      # Poids divisé par 2 tous les 7 jours
    SUSPEND_THRESHOLD: float = 0.1   # Auto-suspension sous ce seuil
    USE_BOOST: float = 0.1           # Boost à chaque activation

    # Quotas par mode (class-level)
    MODE_QUOTAS = {
        "light": 15,
        "normal": 50,
        "heavy": 100,
        "max": 200
    }
```

**Formule de decay :**
```
days_since = (now - last_active).days
decay_factor = 0.5^(days_since / HALF_LIFE_DAYS)
weight = weight * decay_factor
```

**Suspension automatique :**
- Si `weight < SUSPEND_THRESHOLD` → Thread suspendu (pas supprimé)
- Si threads actifs > `MODE_QUOTAS[mode]` → Threads les plus légers suspendus

**Message :**
```python
@dataclass
class Message:
    id: str                    # "msg_YYYYMMdd_HHMMSS_hex"
    content: str               # Texte du message
    source: str                # "user" | "assistant"
    timestamp: datetime
    metadata: dict             # source_type, file_path, etc.
```

### 2.2 ThinkBridge

Connexion sémantique entre deux threads, créée automatiquement par gossip.

```python
@dataclass
class ThinkBridge:
    id: str                    # "bridge_YYYYMMdd_HHMMSS_hex"
    source_id: str             # Thread source
    target_id: str             # Thread cible

    # Sémantique
    relation_type: BridgeType  # EXTENDS | CONTRADICTS | DEPENDS | REPLACES | CHILD_OF | SIBLING
    reason: str                # Explication LLM de la connexion
    shared_concepts: List[str] # Topics communs

    # Confiance
    confidence: float          # 0.0-1.0 (embedding similarity ou LLM)
    status: BridgeStatus       # ACTIVE | WEAK | INVALID

    # Propagation gossip
    propagated_from: Optional[str]  # Bridge parent si propagé
    propagation_depth: int          # 0=direct, 1+=propagé

    # Métriques d'usage et decay
    use_count: int
    last_used: Optional[datetime]
    weight: float                       # 1.0 initial, décroit avec le temps

    # Constantes de decay (class-level)
    HALF_LIFE_DAYS: float = 3.0         # Poids divisé par 2 tous les 3 jours
    DEATH_THRESHOLD: float = 0.05       # Bridge supprimé sous ce seuil
    USE_BOOST: float = 0.1              # Boost à chaque utilisation
```

**Formule de decay (bridges) :**
```
reference = last_used if last_used else created_at
days_since = (now - reference).days
decay_factor = 0.5^(days_since / HALF_LIFE_DAYS)
weight = weight * decay_factor
```

**Mort synaptique :**
- Si `weight < DEATH_THRESHOLD` → Bridge supprimé définitivement
- Si `weight < 0.3` → Status = WEAK

**Types de relations :**
| Type | Description | Détection |
|------|-------------|-----------|
| `CHILD_OF` | Thread enfant | `parent_id` défini |
| `SIBLING` | Frères (même parent) | Parent commun |
| `EXTENDS` | Prolonge/approfondit | Créé après + similarité élevée |
| `DEPENDS` | Dépendance | Détecté par LLM |
| `CONTRADICTS` | Contradiction | Détecté par LLM |
| `REPLACES` | Remplace/obsolète | Détecté par LLM |

---

## 3. Pipeline de Traitement

### 3.1 Capture (PostToolUse)

```
Tool Output
    │
    ▼
┌─────────────────────────────────────┐
│ 1. Filtrage heuristique             │
│    - Supprime tags IDE (<ide_*>)    │
│    - Ignore JSON pure tools         │
│    - Min 30 chars                   │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│ 2. Nettoyage (cleaner.py)           │
│    - Parse JSON/dict récursif       │
│    - Extrait contenu sémantique     │
│    - Truncate intelligent (5000ch)  │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│ 3. Extraction LLM (extractor.py)    │
│    - Titre (sujet, pas action)      │
│    - Summary, subjects, concepts    │
│    - Questions, décisions           │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│ 4. Décision ThreadManager           │
│    - NEW_THREAD: sim < 0.35         │
│    - CONTINUE: sim > 0.35           │
│    - FORK: sous-sujet détecté       │
│    - REACTIVATE: suspendu + sim>0.5 │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│ 5. Gossip Propagation               │
│    - Embedding du thread            │
│    - Find similar (>0.5)            │
│    - Create ThinkBridges            │
└─────────────────────────────────────┘
```

**Mapping Tool → SourceType :**
```python
SOURCE_MAP = {
    "Read": "read",
    "Write": "write",
    "Edit": "write",
    "Glob": "read",
    "Grep": "read",
    "Task": "task",
    "WebFetch": "fetch",
    "WebSearch": "fetch",
    "Bash": "command",
    "UserPrompt": "prompt",
}
```

**Mapping SourceType → OriginType :**
```python
SOURCE_TO_ORIGIN = {
    "prompt": OriginType.PROMPT,
    "read": OriginType.FILE_READ,
    "write": OriginType.FILE_READ,
    "task": OriginType.TASK,
    "fetch": OriginType.FETCH,
    "response": OriginType.PROMPT,
    "command": OriginType.PROMPT,
}
```

### 3.2 Coherence-Based Child Linking (Phase 14)

Pour les outils de contexte (Glob, Grep), le contenu subséquent peut devenir enfant automatiquement.

```
[Glob/Grep Output]
    │
    ▼
┌─────────────────────────────────┐
│ Créer Thread + set pending_ctx  │
│ {thread_id, content, timestamp} │
└─────────────────┬───────────────┘
                  │
    [Prochain contenu non-Glob/Grep]
                  │
                  ▼
┌─────────────────────────────────┐
│ Coherence Check (Haiku LLM)     │
│ Score 0.0 - 1.0                 │
└─────────────────┬───────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
 > 0.6        0.3-0.6        < 0.3
 CHILD        ORPHAN         FORGET
(fork)     (normal flow)    (skip)
```

**Context Tools :** `{"Glob", "Grep"}` (extensible)

**Expiration :** 10 minutes

### 3.3 Injection (UserPromptSubmit)

```
User Prompt
    │
    ▼
┌─────────────────────────────────┐
│ 0. CLI Command Detection (v3)   │
│    Pattern: ^ai\s+(command)     │
│    → Execute + inject result    │
│    → Skip rest of pipeline      │
└─────────────────┬───────────────┘
                  │ (if not CLI command)
                  ▼
┌─────────────────────────────────┐
│ 1. Détection règles utilisateur │
│    "rappelle-toi:", "toujours"  │
│    → save user_rules.json       │
└─────────────────┬───────────────┘
                  ▼
┌─────────────────────────────────┐
│ 2. Capture prompt vers daemon   │
│    (min 50 chars, skip "ok")    │
└─────────────────┬───────────────┘
                  ▼
┌─────────────────────────────────┐
│ 3. Memory Retrieval             │
│    - Embed message              │
│    - Find similar threads       │
│    - Hybrid reactivation        │
│    - Load user rules            │
└─────────────────┬───────────────┘
                  ▼
┌─────────────────────────────────┐
│ 4. GuardCode Check              │
│    - Complexity detection       │
│    - Quick-fix warning          │
│    - Choices reminder           │
└─────────────────┬───────────────┘
                  ▼
┌─────────────────────────────────┐
│ 5. Inject <system-reminder>     │
│    Prepend to original message  │
└─────────────────────────────────┘
```

### 3.3.1 CLI in Prompt (v3.0.0)

Le hook UserPromptSubmit détecte les commandes CLI dans le prompt et les exécute directement.

**Pattern de détection:**
```python
CLI_COMMAND_PATTERN = r'^ai\s+(status|threads?|bridges?|search|reindex|health|daemon|mode|help)(?:\s+(.*))?$'
```

**Commandes supportées:**
| Commande | Exemple | Description |
|----------|---------|-------------|
| `ai status` | `ai status` | Vue d'ensemble mémoire |
| `ai threads` | `ai threads` | Liste threads actifs |
| `ai thread` | `ai thread abc123` | Détails d'un thread |
| `ai bridges` | `ai bridges` | Liste bridges |
| `ai search` | `ai search auth` | Recherche sémantique |
| `ai health` | `ai health` | Vérification santé |
| `ai daemon` | `ai daemon status` | Contrôle daemon |
| `ai mode` | `ai mode heavy` | Voir/changer mode |
| `ai help` | `ai help` | Aide CLI |

**Format d'injection:**
```xml
<system-reminder>
CLI Command: ai status

=== AI Smartness Status ===
Project: MyProject
Threads: 45 total
...
</system-reminder>

The user executed a CLI command. Summarize the result above briefly.
```

### 3.4 Réactivation Hybride

```
User Message
    │
    ▼
Embedding Similarity avec threads suspendus
    │
    ├── > 0.35 ──────────► Auto-réactivation (sans LLM)
    │
    ├── 0.15-0.35 ───────► LLM Haiku décide
    │                      "Ce message concerne-t-il ce thread?"
    │
    └── < 0.15 ──────────► Pas de réactivation
```

### 3.5 Compact (PreCompact @ 95%)

```
Context 95% full
    │
    ▼
┌─────────────────────────────────┐
│ 1. Collect active threads (5)   │
│ 2. Get recent messages          │
│ 3. LLM synthesis generation:    │
│    - summary                    │
│    - decisions_made             │
│    - open_questions             │
│    - key_insights               │
└─────────────────┬───────────────┘
                  ▼
┌─────────────────────────────────┐
│ Save: db/synthesis/synthesis_*  │
│ Inject: SESSION CONTINUATION    │
└─────────────────────────────────┘
```

---

## 4. Seuils et Constantes

### 4.1 Similarité & Décisions

| Contexte | Seuil | Action |
|----------|-------|--------|
| Thread actif | > 0.35 | CONTINUE |
| Thread actif | < 0.35 | NEW_THREAD |
| Thread suspendu | > 0.50 | REACTIVATE |
| Réactivation auto | > 0.35 | Sans LLM |
| Réactivation borderline | 0.15-0.35 | LLM décide |
| Gossip bridge | > 0.50 | Créer bridge |
| Topic boost | +0.15 | Si topic identique |

### 4.2 Calcul de Similarité

```
similarity = 0.7 × embedding_sim + 0.3 × topic_overlap + topic_boost
```

- `embedding_sim`: Cosine similarity (embeddings 384-dim)
- `topic_overlap`: Ratio de topics communs
- `topic_boost`: +0.15 si au moins 1 topic commun

### 4.3 Coherence (Child Linking)

| Score | Décision | Signification |
|-------|----------|---------------|
| > 0.6 | `child` | Forte relation → thread enfant |
| 0.3-0.6 | `orphan` | Faible relation → thread indépendant |
| < 0.3 | `forget` | Bruit → ignorer |

### 4.4 Mode et Quotas de Threads

| Mode | Threads actifs max | Cas d'usage |
|------|-------------------|-------------|
| light | 15 | Petits projets, tests |
| normal | 50 | Développement standard |
| heavy | 100 | Gros projets, équipes |
| max | 200 | Environnements complexes |

**Changement de mode :**
```bash
ai mode normal    # Passe en mode normal
ai mode heavy     # Passe en mode heavy
ai mode status    # Affiche mode actuel
```

Si le nouveau quota est inférieur au nombre de threads actifs, les threads les plus légers sont automatiquement suspendus.

### 4.5 Decay & Pruning

| Entité | Half-life | Seuil mort/suspension | Action |
|--------|-----------|----------------------|--------|
| ThinkBridge | 3 jours | 0.05 | Suppression |
| Thread | 7 jours | 0.1 | Suspension |

**Boost à l'usage :** +0.1 (capped à 1.0)

**Commandes de pruning :**
```bash
ai threads --prune    # Decay + suspension threads
ai bridges --prune    # Decay + suppression bridges morts
```

### 4.6 Timeouts

| Opération | Timeout |
|-----------|---------|
| Extraction LLM | 30s |
| Coherence check | 15s |
| Synthesis | 60s |
| Socket daemon | 0.5s |

### 4.7 Limites de Contenu

| Élément | Limite |
|---------|--------|
| Contenu extraction | 3000 chars |
| Contenu coherence | 1500 chars/input |
| Contenu thread | 5000 chars |
| Prompt min capture | 50 chars |
| Topic min | 3 chars |
| User rules max | 20 rules |
| User rule min | 10 chars |

---

## 5. Embeddings

### 5.1 Configuration

- **Modèle principal**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Fallback**: TF-IDF avec hash déterministe

### 5.2 TF-IDF Fallback

Si sentence-transformers n'est pas installé :
1. Tokenization: lowercase, alphanumeric
2. Stopwords filtering
3. Hash déterministe → index dans vecteur 384-dim
4. Normalisation L2

### 5.3 Singleton

```python
embedding_manager = get_embedding_manager()
embedding_manager.embed("text")           # → List[float] 384-dim
embedding_manager.similarity(vec1, vec2)  # → float 0.0-1.0
```

---

## 6. GuardCode

### 6.1 Règles

| Règle | Déclencheur | Rappel |
|-------|-------------|--------|
| `enforce_plan_mode` | Keywords complexité (implement, refactor, create) | "Considère d'utiliser plan mode" |
| `warn_quick_solutions` | Keywords rapides (quick, hack, just) | "Évalue les alternatives" |
| `require_all_choices` | Detection choix | "Présente toutes les options" |

### 6.2 Keywords Complexité (FR)

```python
["implémenter", "refactorer", "créer", "construire", "ajouter une fonctionnalité",
 "nouveau système", "architecture", "migration", "intégration", "optimiser"]
```

### 6.3 Configuration

```json
{
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true,
    "require_all_choices": true
  }
}
```

---

## 7. Daemon

### 7.1 Architecture

- **Type**: Process background (fork double)
- **Communication**: Unix socket (`.ai/processor.sock`)
- **PID file**: `.ai/processor.pid`
- **Log**: `.ai/processor.log`

### 7.2 Modules chargés (une fois)

1. `StorageManager` - Persistance
2. `ThreadManager` - Lifecycle threads
3. `GossipPropagator` - Création bridges
4. `EmbeddingManager` - Vecteurs

### 7.3 Requêtes supportées

| Requête | Réponse |
|---------|---------|
| `{"ping": true}` | `{"pong": true, "pid": N}` |
| `{"status": true}` | Stats daemon |
| `{"shutdown": true}` | Arrêt graceful |
| `{"tool": "X", "content": "..."}` | Process capture |

### 7.4 Auto-Pruning Timer (v3.0.0)

Le daemon exécute automatiquement le pruning toutes les 5 minutes :

```python
PRUNE_INTERVAL_SECONDS = 300  # 5 minutes

def _prune_timer_loop(self):
    """Thread background qui exécute le pruning périodique."""
    while self.running:
        time.sleep(PRUNE_INTERVAL_SECONDS)
        # Prune threads (decay + suspend)
        self.thread_manager.prune_threads()
        # Prune bridges (decay + delete dead)
        self.gossip.prune_dead_bridges()
```

**Actions du pruning:**
1. Appliquer decay à tous les threads actifs
2. Suspendre threads avec weight < 0.1
3. Appliquer decay à tous les bridges
4. Supprimer bridges avec weight < 0.05

### 7.5 Anti-Loop Guard

Variable d'environnement `AI_SMARTNESS_V2_HOOK_RUNNING=1` :
- Définie pendant les appels LLM internes
- Empêche les hooks de se déclencher sur les extractions

---

## 8. Storage

### 8.1 Structure

```
.ai/
├── config.json              # Configuration projet
├── user_rules.json          # Règles utilisateur
├── processor.sock           # Socket daemon
├── processor.pid            # PID daemon
├── processor.log            # Log daemon
├── capture.log              # Log capture hook
├── inject.log               # Log inject hook
├── compact.log              # Log compact hook
└── db/
    ├── threads/
    │   ├── _active.json     # Index threads actifs
    │   ├── _suspended.json  # Index threads suspendus
    │   └── thread_*.json    # Threads individuels
    ├── bridges/
    │   ├── _index.json      # Index source/target
    │   └── bridge_*.json    # Bridges individuels
    └── synthesis/
        └── synthesis_*.json # Synthèses compaction
```

### 8.2 Indexation

**Threads** (`_active.json`, `_suspended.json`):
```json
["thread_20260130_123456_abc123", "thread_20260130_123457_def456"]
```

**Bridges** (`_index.json`):
```json
{
  "by_source": {
    "thread_id": ["bridge_id1", "bridge_id2"]
  },
  "by_target": {
    "thread_id": ["bridge_id3"]
  }
}
```

---

## 9. Configuration

### 9.1 config.json

```json
{
  "project_name": "my_project",
  "language": "fr",
  "version": "3.0.0",
  "initialized_at": "2026-01-30T12:00:00",
  "mode": "normal",
  "settings": {
    "extraction_model": null,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "auto_capture": true,
    "active_threads_limit": 50
  },
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true,
    "require_all_choices": true
  },
  "llm": {
    "extraction_model": null,
    "claude_cli_path": null
  }
}
```

### 9.2 Modèles par Mode

| Mode | Modèle Guardian |
|------|-----------------|
| light | claude-haiku-3-5-20250620 |
| normal | claude-sonnet-4-20250514 |
| heavy | claude-opus-4-5-20250514 |
| max | claude-opus-4-5-20250514 |

---

## 10. CLI

### 10.1 Commandes

```bash
ai status                       # Vue d'ensemble
ai threads [--status X]         # Lister threads
ai threads --show-weight        # Afficher poids avec indicateurs
ai threads --prune              # Appliquer decay + suspension
ai thread <id>                  # Détails thread
ai bridges [--thread ID]        # Lister bridges
ai bridges --show-weight        # Afficher poids bridges
ai bridges --prune              # Appliquer decay + supprimer morts
ai search <query>               # Recherche sémantique
ai health                       # Vérification santé
ai reindex                      # Recalculer embeddings
ai daemon [status|start|stop]   # Gérer daemon
ai mode [status|light|normal|heavy|max]  # Voir/changer mode
```

### 10.2 Installation CLI

```bash
/path/to/ai_smartness_v2/install.sh /path/to/project
```

L'installateur :
1. Sélection langue (en/fr/es)
2. Sélection mode (light/normal/heavy/max)
3. Installation sentence-transformers si absent
4. Configuration hooks dans `.claude/settings.json`
5. Installation CLI dans `~/.local/bin/ai`

---

## 11. Hooks Claude Code

### 11.1 Configuration

`.claude/settings.json`:
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": ["python3 /path/to/hooks/inject.py"]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": ["python3 /path/to/hooks/capture.py"]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": ["python3 /path/to/hooks/compact.py"]
      }
    ]
  }
}
```

### 11.2 Format d'entrée

**PostToolUse:**
```json
{
  "tool_name": "Read",
  "tool_input": {"file_path": "/path/to/file"},
  "tool_response": {"content": "..."}
}
```

**UserPromptSubmit:**
```json
{
  "prompt": "User message here"
}
```
ou (VSCode):
```json
{
  "message": "User message here"
}
```

---

## 12. Extraction LLM

### 12.1 Prompt (exemple FR pour "prompt")

```
Tu es un analyseur sémantique pour une mémoire d'IA.
Analyse ce message utilisateur et extrais:

MESSAGE:
{content}

Réponds en JSON strict:
{
  "title": "Titre du sujet (3-5 mots, noms pas verbes)",
  "intent": "Ce que l'utilisateur veut (1 phrase)",
  "summary": "Résumé (1-2 phrases)",
  "subjects": ["sujet1", "sujet2"],
  "questions": ["question posée ou implicite"],
  "decisions": ["décision prise"],
  "key_concepts": ["concept technique important"]
}
```

### 12.2 Prompts par source_type

| Source | Focus |
|--------|-------|
| `prompt` | Intention utilisateur |
| `read` | Structure et contenu fichier |
| `write` | Modifications apportées |
| `task` | Résultat sous-agent |
| `fetch` | Contenu web |
| `response` | Réponse assistant |
| `command` | Output commande shell |

---

## 13. Métriques de Santé

```bash
ai health
```

| Métrique | Cible | Description |
|----------|-------|-------------|
| Daemon status | Running | Daemon actif |
| Embedding coverage | 100% | Tous threads embeddings |
| Continuation rate | > 20% | % threads multi-messages |
| Bridge ratio | > 0.5 | Bridges/threads |

---

## 14. Fonctionnalités v2.7-v2.9

### 14.1 Universal Coherence Chain (v2.7.0)

Vérification de cohérence entre output tool et réponse agent :
- Les outils de contexte (Glob, Grep) créent un `pending_context`
- Le prochain contenu non-context est vérifié pour cohérence
- Score > 0.6 → fork comme thread enfant
- Score 0.3-0.6 → thread indépendant
- Score < 0.3 → ignoré

### 14.2 Bridge Weight Decay (v2.8.0)

Synaptic pruning - les bridges inutilisés meurent :
- Decay exponentiel avec half-life de 3 jours
- Boost de +0.1 à chaque utilisation
- Suppression définitive quand weight < 0.05
- Status WEAK quand weight < 0.3

### 14.3 Thread Decay & Mode Management (v2.9.0)

Neuronal dormancy - les threads inactifs s'endorment :
- Decay exponentiel avec half-life de 7 jours
- Boost de +0.1 à chaque activation
- Suspension (pas suppression) quand weight < 0.1
- Quota dynamique par mode (light/normal/heavy/max)
- Changement de mode à la volée avec `ai mode`

### 14.4 Weight System Alignment (v2.9.1)

Unification du système de poids threads/bridges :
- Thread.weight initialisé à 1.0 (au lieu de 0.5)
- FORK threads héritent du poids parent
- Suppression de `_update_weight()` (conflit avec decay)
- `add_message()` et `reactivate()` passent par `boost_weight()`

### 14.5 CLI in Prompt + Auto-Pruning (v3.0.0)

Deux nouvelles fonctionnalités majeures :

**CLI dans le Prompt:**
- Détection pattern `^ai\s+(command)` dans UserPromptSubmit
- Exécution CLI et injection résultat en `<system-reminder>`
- Commandes: status, threads, thread, bridges, search, health, daemon, mode, help

**Daemon Auto-Pruning:**
- Timer de 5 minutes pour pruning automatique
- Decay appliqué à tous les threads et bridges
- Suspension threads dormants, suppression bridges morts
- Zero intervention utilisateur requise

---

## 15. Évolutions Futures

### 15.1 Extensibilité Coherence

Le set `CONTEXT_TOOLS` peut être étendu :
```python
CONTEXT_TOOLS = {"Glob", "Grep", "Read", "Task", "WebFetch"}
```

### 15.2 Seuils Dynamiques

Les seuils de cohérence pourront être ajustés dynamiquement par le LLM basé sur :
- Performance passée (faux positifs/négatifs)
- Type de projet
- Patterns utilisateur

### 15.3 Méta-cognition Avancée

- Auto-évaluation de la qualité des threads
- Consolidation automatique de threads similaires
- Réactivation intelligente des threads suspendus

---

## 16. Contraintes Non-Négociables

| Règle | Justification |
|-------|---------------|
| 100% LLM pour sémantique | Regex inopérantes pour cette complexité |
| Zéro pollution prompt | Utilisateur ne voit pas les mécanismes |
| 100% transparent | Zéro action utilisateur requise |
| 100% local | Aucune donnée externe |
| Daemon background | Latence minimale |

---

## Appendice A: Dépendances

### Python (requises)
- `dataclasses` (stdlib)
- `json` (stdlib)
- `pathlib` (stdlib)
- `socket` (stdlib)
- `threading` (stdlib)
- `subprocess` (stdlib)
- `logging` (stdlib)

### Python (optionnelles)
- `sentence-transformers` - Embeddings haute qualité
- `torch` - Backend sentence-transformers

### External
- `claude` CLI - Appels LLM via subprocess

---

## Appendice B: Logs

| Fichier | Contenu |
|---------|---------|
| `processor.log` | Daemon main loop, captures |
| `capture.log` | Hook capture decisions |
| `inject.log` | Hook inject context |
| `compact.log` | Hook compact synthesis |
| `daemon_stderr.log` | Erreurs daemon |

Format: `[YYYY-MM-DD HH:MM:SS] LEVEL: message`
