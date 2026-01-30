# AI Smartness v2 - Specification

## Meta

- **Version**: 2.0.0
- **Date**: 2026-01-29
- **Auteur**: Claude (Opus 4.5) + User
- **Status**: Implemented

---

## 1. Vision

AI Smartness v2 est une **couche de méta-cognition** pour agents LLM, pas simplement une mémoire.

### Objectif principal
Donner à un agent LLM une **mémoire persistante** qui lui permet de :
- Reprendre un projet après des semaines/mois comme si l'utilisateur était parti boire un café
- Naviguer dans des projets complexes sans drift ni hallucinations
- Maintenir une cohérence sémantique sur des sessions de 15+ heures

### Métaphore neuronale
| Concept | Analogie | Rôle |
|---------|----------|------|
| **Thread** | Neurone | Sujet de travail actif |
| **ThinkBridge** | Synapse | Connexion sémantique entre threads |
| **Thread archived** | Neurone dormant | Sujet archivé mais réactivable |
| **Memory Injection** | Signal | Contexte restauré à chaque prompt |

---

## 2. Contraintes Non-Négociables

### 2.1 Traitement
| Règle | Justification |
|-------|---------------|
| **100% LLM pour le raisonnement** | Les regex sont inopérantes pour ce niveau de complexité |
| **Zéro regex pour la sémantique** | Seul le LLM peut comprendre le sens |
| **Heuristiques OK pour le bruit** | Filtrer les tags IDE, JSON tool outputs |

### 2.2 Expérience utilisateur
| Règle | Justification |
|-------|---------------|
| **100% transparent** | Zéro action utilisateur requise |
| **Zéro pollution du prompt** | L'utilisateur ne doit pas voir les mécanismes internes |
| **Persistance longue durée** | Semaines/mois sans perte de contexte |

### 2.3 Architecture
| Règle | Justification |
|-------|---------------|
| **Daemon en arrière-plan** | Traitement rapide, modules chargés une seule fois |
| **Embeddings pour retrieval** | Rapide, scalable |
| **Installation automatisée** | sentence-transformers installé par install.sh |

---

## 3. Architecture

### 3.1 Entités (2 seulement)

#### Thread
Le Thread est l'unique entité de travail. Il représente un **sujet/flux de travail**.

```python
@dataclass
class Thread:
    id: str
    title: str  # Généré par LLM, sémantiquement riche
    status: Literal["active", "suspended", "archived"]

    # Contenu
    messages: List[Message]  # Historique complet
    summary: str  # Résumé LLM du thread
    topics: List[str]  # Concepts clés extraits

    # Méta-info (origine et évolution)
    origin_type: Literal["prompt", "file_read", "task", "fetch", "split"]
    drift_history: List[str]  # ["prompt", "file_read", "code_write"]

    # Relations
    parent_id: Optional[str]
    child_ids: List[str]

    # Pondération (calculée par sollicitation)
    weight: float  # 0.0 - 1.0
    last_active: datetime

    # Embeddings
    embedding: List[float]  # Vecteur pour similarité (384 dimensions)
```

#### ThinkBridge
Connexion sémantique entre threads, propagée en mode "gossip".

```python
@dataclass
class ThinkBridge:
    id: str
    source_id: str
    target_id: str

    # Type de relation (déterminé par LLM)
    relation_type: Literal["extends", "contradicts", "depends", "replaces", "child_of"]

    # Sémantique
    reason: str  # Explication LLM de la connexion

    # Confiance (calculée, pas hardcodée)
    confidence: float  # Basée sur embedding similarity

    # Propagation gossip
    propagation_depth: int  # 0 = direct, 1+ = propagé
```

### 3.2 Composants Système

| Composant | Fichier | Rôle |
|-----------|---------|------|
| **Daemon** | `daemon/processor.py` | Traitement en arrière-plan |
| **Client** | `daemon/client.py` | Communication rapide avec daemon |
| **Hook Capture** | `hooks/capture.py` | Capture PostToolUse |
| **Hook Injection** | `hooks/inject.py` | Injection UserPromptSubmit |
| **Hook Compact** | `hooks/compact.py` | Synthèse PreCompact |
| **Memory Retriever** | `intelligence/memory_retriever.py` | Récupération contexte pertinent |
| **Thread Manager** | `intelligence/thread_manager.py` | Cycle de vie threads |
| **Gossip Propagator** | `intelligence/gossip.py` | Propagation bridges |
| **Embeddings** | `processing/embeddings.py` | Vecteurs sémantiques |
| **Extractor** | `processing/extractor.py` | Extraction LLM |

---

## 4. Pipeline de Traitement

### 4.1 Capture (PostToolUse)

```
[Tool Result] → [Hook capture.py] → [Daemon via socket]
                                           ↓
[Noise Filter] → [LLM Extraction] → [Thread Decision] → [Storage]
                                           ↓
                                   [Gossip Propagation]
```

### 4.2 Thread Decision

| Décision | Condition | Action |
|----------|-----------|--------|
| `NEW_THREAD` | Similarité < 0.35 avec tous actifs | Créer nouveau thread |
| `CONTINUE` | Similarité > 0.35 avec actif | Ajouter au thread |
| `REACTIVATE` | Similarité > 0.50 avec suspendu | Réactiver thread |
| `FORK` | Sous-sujet détecté | Créer thread enfant |

### 4.3 Memory Injection (UserPromptSubmit)

```
[User Message] → [Hook inject.py]
                       ↓
[Memory Retriever] → [Find similar threads]
                       ↓
[Build context string] → [Inject as <system-reminder>]
                       ↓
[Claude receives: context + message]
```

Exemple d'injection :
```xml
<system-reminder>
AI Smartness Memory Context:

Current thread: "JWT Authentication"
Summary: Implementing refresh token rotation...

Related threads:
- "Database Schema" - User tables
- "Security Audit" - Token policies

User rules:
- always make a plan before implementation
</system-reminder>
```

### 4.4 User Rules Detection

Patterns détectés automatiquement dans les messages utilisateur :
- `rappelle-toi : <rule>`
- `règle : <rule>`
- `toujours <action>`
- `jamais <action>`
- `remember: <rule>`
- `rule: <rule>`
- `always <action>`
- `never <action>`

Règles stockées dans `ai_smartness_v2/.ai/user_rules.json`.

---

## 5. Seuils de Continuation et Réactivation Hybride

### Valeurs

| Contexte | Seuil | Description |
|----------|-------|-------------|
| Thread actif | 0.35 | Similarité minimale pour continuer |
| Thread suspendu (auto) | 0.35 | Haute confiance → réactivation automatique |
| Thread suspendu (LLM) | 0.15-0.35 | Zone borderline → LLM décide |
| Topic boost | +0.15 | Bonus si topic identique |

### Calcul de similarité

```
similarity = 0.7 * embedding_sim + 0.3 * topic_overlap + topic_boost
```

- `embedding_sim`: Cosine similarity entre embeddings
- `topic_overlap`: Ratio de topics communs
- `topic_boost`: +0.15 si au moins un topic identique

### Réactivation Hybride LLM

La réactivation des threads suspendus utilise une approche **hybride** combinant embeddings et raisonnement LLM :

```
Message utilisateur
        ↓
   Embedding similarity
        ↓
┌───────┴───────────────┐
│                       │
Sim > 0.35             0.15 < Sim < 0.35         Sim < 0.15
(haute confiance)       (borderline)              (basse)
│                       │                         │
↓                       ↓                         ↓
Auto-réactivation       LLM Haiku décide          Pas de
(sans LLM)              "Ce message concerne-     réactivation
                         t-il ce thread?"
```

**Avantages** :
- **Performance** : LLM appelé uniquement pour ~20% des cas (borderline)
- **Précision** : Relations sémantiques subtiles capturées (ex: "meta cognition" ↔ "ai_smartness")
- **Économie** : Haiku économique (~$0.00025/appel)

### Libération de Slots

Quand la limite de threads actifs est atteinte et qu'un thread doit être réactivé :

1. Identification des threads actifs non pertinents au message courant
2. Sélection du thread avec le plus faible poids (`weight`)
3. Suspension automatique de ce thread
4. Réactivation du thread cible

```python
# Critères de sélection pour suspension
1. Thread non présent dans les résultats de similarité
2. Poids (weight) le plus faible
3. Date last_active la plus ancienne
```

### Embeddings

| Méthode | Condition | Qualité |
|---------|-----------|---------|
| sentence-transformers | Si installé | Haute (semantic) |
| TF-IDF fallback | Si non installé | Moyenne (lexical) |

L'installateur installe sentence-transformers automatiquement.

---

## 6. Storage

### Structure

```
ai_smartness_v2/.ai/
├── config.json           # Configuration
├── user_rules.json       # Règles utilisateur
├── processor.pid         # PID daemon
├── processor.sock        # Socket daemon
├── processor.log         # Logs daemon
├── inject.log            # Logs injection
├── daemon_stderr.log     # Erreurs daemon
└── db/
    ├── threads/          # Thread JSON files
    │   └── *.json
    ├── bridges/          # ThinkBridge JSON files
    │   └── *.json
    └── synthesis/        # Synthèses compaction
```

---

## 7. CLI Commands

```bash
ai status              # Vue d'ensemble
ai threads             # Lister threads
ai thread <id>         # Détails thread
ai bridges             # Lister bridges
ai search <query>      # Recherche sémantique
ai health              # Vérification santé
ai reindex             # Recalculer embeddings
ai daemon              # Status daemon
ai daemon start        # Démarrer daemon
ai daemon stop         # Arrêter daemon
```

---

## 8. Hooks Integration

| Hook | Script | Timing | Action |
|------|--------|--------|--------|
| `UserPromptSubmit` | inject.py | Pre-prompt | Injection mémoire + GuardCode |
| `PostToolUse` | capture.py | Post-tool | Capture et envoi au daemon |
| `PreCompact` | compact.py | 95% context | Synthèse et sauvegarde |

---

## 9. Installation

```bash
/path/to/ai_smartness_v2-DEV/install.sh /path/to/project
```

### Modes disponibles

| Mode | Threads actifs | Description | Cas d'usage |
|------|----------------|-------------|-------------|
| **MAX** | 200 | Mémoire maximale | Projets complexes, sessions 15+ heures |
| **Heavy** | 100 | Analyse profonde | Gros projets |
| **Normal** | 50 | Équilibré | Usage standard |
| **Light** | 15 | Rapide & économique | Petits projets |

Le mode **MAX** est recommandé pour :
- Projets avec de nombreux composants interdépendants
- Sessions de travail de 15+ heures
- Contextes où la perte de mémoire est critique

### Ce que fait l'installateur

1. Sélection langue (en/fr/es)
2. Sélection mode (MAX/heavy/normal/light)
3. **Installation sentence-transformers** si non présent
4. Détection chemin CLI Claude
5. Copie fichiers avec chemins absolus
6. Configuration hooks dans `.claude/settings.json`
7. Initialisation base de données
8. Installation CLI dans `~/.local/bin/ai`

---

## 10. GuardCode

### Règles

| Règle | Action |
|-------|--------|
| `enforce_plan_mode` | Rappel pour tâches complexes |
| `warn_quick_solutions` | Rappel que simple ≠ meilleur |
| `require_all_choices` | Présenter alternatives |

### Configuration

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

## 11. Métriques de Santé

| Métrique | Cible | Signification |
|----------|-------|---------------|
| Continuation rate | > 20% | % threads avec >1 message |
| Embedding coverage | 100% | Tous threads ont embedding |
| Daemon status | Running | Daemon actif |

Vérifier avec `ai health`.

---

## 12. Phases d'Implémentation

### Phase 1: Core - COMPLETE
- [x] Modèle Thread simplifié
- [x] Storage JSON
- [x] Hook capture basique

### Phase 2: Intelligence - COMPLETE
- [x] Extraction LLM
- [x] Embeddings (sentence-transformers + TF-IDF fallback)
- [x] ThinkBridges avec gossip

### Phase 3: GuardCode - COMPLETE
- [x] Micro-injection contexte
- [x] Enforcement plan mode
- [x] Synthèse à 95%

### Phase 4: Polish - COMPLETE
- [x] Daemon architecture
- [x] CLI complet
- [x] Documentation multilingue

### Phase 5: Memory Injection - COMPLETE
- [x] MemoryRetriever
- [x] User rules detection
- [x] Context injection in inject.py

### Phase 6: Optimizations - COMPLETE
- [x] Seuil 0.35
- [x] Topic boost +0.15
- [x] Daemon CLI control
- [x] Auto-install sentence-transformers

---

## 13. Ce que v2 NE FAIT PAS

| Anti-pattern | Pourquoi |
|--------------|----------|
| Regex pour classification | Inopérant pour la complexité sémantique |
| Seuils hardcodés arbitraires | Décisions basées sur embeddings |
| Stockage du code complet | Uniquement sémantique |
| Envoi de données externes | 100% local |
| Actions utilisateur requises | 100% transparent |
