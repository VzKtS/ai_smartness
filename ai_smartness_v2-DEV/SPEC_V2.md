# AI Smartness v2 - Specification

## Meta

- **Version**: 2.0.0
- **Date**: 2026-01-28
- **Auteur**: Claude (Opus 4.5) + User
- **Status**: Draft - En attente validation

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
| **Zéro valeur hardcodée** | Pas de timestamps/seuils arbitraires |
| **Décisions par raisonnement LLM** | Merge, split, affiliate = décisions intelligentes |
| **Embeddings pour retrieval** | Rapide, pas de bruit, scalable |

---

## 3. Architecture Simplifiée

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

    # Méta-info (origine et évolution)
    origin_type: Literal["prompt", "file_read", "task", "fetch", "split"]
    drift_history: List[str]  # ["prompt", "file_read", "code_write"]

    # Relations
    parent_id: Optional[str]
    child_ids: List[str]

    # Pondération (calculée par sollicitation)
    weight: float  # 0.0 - 1.0
    last_active: datetime
    activation_count: int

    # Embeddings
    embedding: List[float]  # Vecteur pour similarité
    topics_embedding: List[float]  # Vecteur des topics
```

**Cycle de vie:**
```
[Nouveau sujet] → Thread créé (status=active)
       ↓
[Inactivité / faible poids] → Thread suspendu (status=suspended)
       ↓
[Longue inactivité] → Thread archivé (status=archived)
       ↓
[Sujet revient] → Thread réactivé (status=active)
                  → LLM décide: merge OU parent/child affiliation
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
    shared_concepts: List[str]  # Concepts partagés

    # Confiance (calculée, pas hardcodée)
    confidence: float  # Basée sur embedding similarity

    # Propagation gossip
    propagated_from: Optional[str]  # ID du bridge parent si propagé
    propagation_depth: int  # 0 = direct, 1+ = propagé
```

### 3.2 Ce qui disparaît

| v1 | v2 | Raison |
|----|----|----|
| Fragment | Absorbé dans Thread | Chaque message/interaction = fragment implicite |
| MemBloc | Thread.status=archived | Simplification |
| Archive | Thread.status=archived | Simplification |
| Graph nodes/edges séparés | Embeddings + ThinkBridges | Plus puissant |

---

## 4. Pipeline de Traitement

### 4.1 Capture (Input)

```
[Source] → [Pré-filtre heuristique] → [Extraction LLM] → [Embedding] → [Storage]
```

#### Sources et pré-traitement

| Source | Pré-filtre | Ce qu'on extrait |
|--------|------------|------------------|
| `prompt` | Tags IDE | Intention, sujet principal, questions |
| `read` | Numéros de ligne | But de la lecture, structure, concepts clés |
| `write` | Diff noise | Ce qui a changé, pourquoi |
| `task` | Étapes intermédiaires | Résultat final, décisions prises |
| `fetch` | HTML/CSS | Information recherchée |
| `response` | Formatage | Décisions, specs, solutions |

#### Extraction LLM (pour chaque input significatif)

```json
{
  "type": "prompt",
  "extract": {
    "intent": "L'utilisateur veut comprendre l'architecture de capture",
    "subjects": ["capture", "hooks", "traitement"],
    "questions": ["Comment fonctionne la capture?"],
    "implicit_context": "Discussion sur ai_smartness v2"
  }
}
```

### 4.2 Thread Management

#### Création de thread
```
[Input] → LLM analyse → "Est-ce un nouveau sujet ou continuation?"
                              ↓
                    [Nouveau] → Créer Thread
                    [Continuation] → Ajouter au Thread actif
                    [Fork] → Créer Thread enfant
                    [Retour] → Réactiver Thread archivé
```

#### Décisions Merge/Split/Affiliate (100% LLM)

```python
# Pseudo-code - JAMAIS de seuils hardcodés
def should_merge(thread_a: Thread, thread_b: Thread) -> MergeDecision:
    prompt = f"""
    Thread A: {thread_a.summary}
    Topics A: {thread_a.topics}

    Thread B: {thread_b.summary}
    Topics B: {thread_b.topics}

    Ces threads doivent-ils être:
    1. MERGE: Fusionnés en un seul (même sujet)
    2. PARENT_CHILD: A parent de B ou B parent de A
    3. SIBLINGS: Frères sous un nouveau parent
    4. SEPARATE: Rester séparés

    Raisonne et décide.
    """
    return llm.decide(prompt)
```

### 4.3 Gossip Propagation (ThinkBridges)

```
[Thread A modifié]
       ↓
[Calcul embedding A']
       ↓
[Pour chaque Thread B avec bridge vers A]
       ↓
[Similarity(A', B) > dynamic_threshold?]
       ↓
[Oui] → Propager: créer/renforcer bridges B→C pour tous C liés à A
[Non] → Ne rien faire
```

Le `dynamic_threshold` n'est PAS hardcodé - il est calculé par le LLM en fonction du contexte.

### 4.4 Context Window Management

À 95% de la fenêtre contextuelle:

```
1. LLM génère synthèse de la conversation actuelle
2. Synthèse inclut:
   - Décisions prises
   - Questions ouvertes
   - État actuel du travail
   - Threads actifs avec résumés
3. Synthèse réinjectée après compactage
4. Utilisateur ne voit RIEN de ce processus
```

---

## 5. GuardCode

### 5.1 Règles d'enforcement

| Règle | Action |
|-------|--------|
| **Plan mode obligatoire** | Bloquer toute modification de code sans plan validé |
| **Pas de solutions rapides** | Rappel systématique que simple ≠ meilleur |
| **Présenter TOUS les choix** | Obligation de montrer alternatives |
| **Pas de drift** | Micro-injection du contexte pour éviter hallucinations |

### 5.2 Micro-injection

À chaque prompt utilisateur, injection invisible de:
```
<context type="guard" hidden="true">
Thread actif: {current_thread.title}
Décisions en cours: {active_decisions}
Focus: {current_focus}
Contraintes: {project_constraints}
</context>
```

Cette injection est **invisible** pour l'utilisateur mais guide l'agent.

---

## 6. Storage

### 6.1 Structure

```
.ai/
├── config.json           # Configuration
├── db/
│   ├── threads/          # Thread JSON files
│   │   ├── {thread_id}.json
│   │   └── _index.json   # Index rapide
│   ├── bridges/          # ThinkBridge JSON files
│   │   ├── {bridge_id}.json
│   │   └── _index.json
│   └── embeddings/       # Vecteurs (format efficace)
│       ├── threads.bin   # Embeddings threads
│       └── meta.json     # Mapping id → offset
├── synthesis/            # Synthèses de compactage
└── logs/                 # Debug (optionnel)
```

### 6.2 Embeddings

- **Modèle**: À définir (local ou API)
- **Dimension**: 384-768 selon modèle
- **Usage**:
  - Similarité entre threads
  - Retrieval de contexte pertinent
  - Détection de topics overlap

---

## 7. Hooks Integration

### 7.1 Points d'intégration Claude Code

| Hook | Timing | Action |
|------|--------|--------|
| `UserPromptSubmit` | Pre-prompt | Micro-injection contexte + GuardCode |
| `PostToolResult` | Post-tool | Capture et extraction |
| `PreCompact` | 95% context | Synthèse et sauvegarde |
| `Stop` | Session end | Flush et archivage |

### 7.2 Format d'injection

```python
def inject_context(user_prompt: str) -> str:
    context = build_context()  # Threads actifs, bridges, focus

    # Injection INVISIBLE (HTML comment ou system tag)
    injection = f"<!-- ai_smartness: {json.dumps(context)} -->"

    return injection + user_prompt
```

---

## 8. Ce que v2 NE FAIT PAS

| Anti-pattern | Pourquoi |
|--------------|----------|
| Regex pour classification | Inopérant pour la complexité sémantique |
| Seuils hardcodés (0.7, 25%, etc.) | Décisions arbitraires sans raisonnement |
| Fragments séparés | Explosion d'entités sans consolidation |
| Edges vides dans un graph | Complexité sans valeur |
| Titres = noms de fichiers | Aucune compréhension du contenu |
| "markdown" comme topic | Bruit technique, pas sémantique |
| Actions utilisateur requises | Casse la transparence |

---

## 9. Métriques de succès

| Métrique | Cible |
|----------|-------|
| Edges créés / fragments | > 2.0 (chaque fragment lié à 2+ autres) |
| Topics vides | < 5% |
| Titres sémantiques | 100% générés par LLM |
| Utilisation context window | < 80% sur session longue |
| Temps reprise après pause | < 30s (synthèse injectée) |

---

## 10. Phases d'implémentation (Proposition)

### Phase 1: Core
- [ ] Modèle Thread simplifié
- [ ] Storage JSON basique
- [ ] Hook capture basique

### Phase 2: Intelligence
- [ ] Extraction LLM pour tous les inputs
- [ ] Embeddings pour similarité
- [ ] ThinkBridges avec gossip

### Phase 3: GuardCode
- [ ] Micro-injection contexte
- [ ] Enforcement plan mode
- [ ] Synthèse à 95%

### Phase 4: Polish
- [ ] Performance optimization
- [ ] Edge cases
- [ ] Documentation

---


