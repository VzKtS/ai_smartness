# AI Smartness v2

**Couche de méta-cognition pour agents Claude Code.**

Un système de mémoire persistante qui transforme Claude Code en un agent capable de maintenir un contexte sémantique sur de longues sessions, de détecter les connexions entre concepts, et de reprendre le travail après des semaines/mois comme si vous étiez juste parti boire un café.

Compatible avec VS Code & Claude Code CLI.

---

## Vision

AI Smartness v2 est une **mémoire de travail inspirée des réseaux neuronaux**:

- **Threads** = Neurones (flux de raisonnement actifs)
- **ThinkBridges** = Synapses (connexions sémantiques entre threads)
- **Gossip** = Propagation du signal à travers le réseau

Le système maintient un **réseau de pensées** où les concepts restent connectés et accessibles, évitant la perte de contexte typique des interactions LLM classiques.

---

## Fonctionnalités Principales

| Fonctionnalité | Description |
|----------------|-------------|
| **Threads** | Unités de travail sémantiques avec titres auto-générés |
| **ThinkBridges** | Connexions automatiques entre threads liés |
| **Propagation Gossip** | Les bridges se propagent dans le réseau quand les concepts évoluent |
| **GuardCode** | Enforcement du plan mode, protection contre le drift |
| **Synthèse 95%** | Préservation automatique du contexte avant compactage |
| **100% Transparent** | Zéro action utilisateur requise |

---

## Architecture v2 (Simplifiée)

### Seulement 2 Entités

| Entité | Rôle |
|--------|------|
| **Thread** | Unité de travail = sujet + messages + résumé + embedding |
| **ThinkBridge** | Connexion sémantique entre deux threads |

### Ce qui a changé depuis v1

| v1 | v2 | Pourquoi |
|----|----|----|
| Fragments | Absorbés dans Threads | Plus simple, chaque message = fragment implicite |
| MemBloc | Thread.status=archived | Modèle unifié |
| Graph complexe | Embeddings + Bridges | Plus puissant, moins d'overhead |
| Seuils hardcodés | Décisions LLM | Intelligent, pas arbitraire |

---

## Installation

```bash
# Dans votre projet cible
/chemin/vers/ai_smartness_v2/install.sh .
```

### Configuration Interactive

1. **Langue**: Anglais, Français ou Espagnol
2. **Mode**: Heavy, Normal ou Light (affecte les limites de threads, pas le coût d'extraction)
3. **Base de données**: Garder les données existantes ou repartir à zéro

### Ce que le Script Fait

- Copie ai_smartness_v2 dans votre projet
- Configure les hooks Claude Code avec des **chemins absolus**
- Détecte le chemin du CLI Claude pour l'extraction LLM
- Initialise la structure de la base de données
- Ajoute les exclusions dans .gitignore et .claudeignore

**Note**: L'extraction utilise toujours **Haiku** (économique, suffisant pour l'extraction sémantique). Votre agent principal peut utiliser n'importe quel modèle (Opus, Sonnet, etc.) - ils sont indépendants.

---

## Commandes CLI

```bash
# Naviguez vers votre projet
cd /votre/projet

# Aperçu du statut
python3 ai_smartness_v2/cli/main.py status

# Lister les threads
python3 ai_smartness_v2/cli/main.py threads
python3 ai_smartness_v2/cli/main.py threads --status active
python3 ai_smartness_v2/cli/main.py threads --limit 20

# Voir un thread spécifique
python3 ai_smartness_v2/cli/main.py thread <thread_id>

# Lister les bridges
python3 ai_smartness_v2/cli/main.py bridges
python3 ai_smartness_v2/cli/main.py bridges --thread <thread_id>

# Recherche sémantique
python3 ai_smartness_v2/cli/main.py search "authentification"
```

---

## Comment ça Marche

### 1. Capture (hook PostToolUse)

Chaque résultat d'outil (Read, Write, Task, etc.) est capturé:
```
[Résultat Outil] → [Filtre Bruit] → [Extraction LLM] → [Décision Thread]
```

### 2. Gestion des Threads

Le LLM décide pour chaque input:
- **NEW_THREAD**: Sujet différent → créer nouveau thread
- **CONTINUE**: Même sujet → ajouter au thread actif
- **FORK**: Sous-sujet → créer thread enfant
- **REACTIVATE**: Ancien sujet revient → réveiller thread archivé

### 3. Propagation Gossip

Quand un thread change:
```
Thread A modifié → Recalcul embedding
                 → Pour chaque thread B connecté
                 → Si similarité haute → propager bridges aux connexions de B
```

### 4. Injection (hook UserPromptSubmit)

Avant chaque prompt utilisateur, contexte invisible injecté:
```html
<!-- ai_smartness: {"active_thread": "...", "decisions": [...]} -->
```

### 5. Synthèse (hook PreCompact)

À 95% de la fenêtre contextuelle:
- Le LLM génère une synthèse de l'état actuel
- Décisions, questions ouvertes, threads actifs
- Injecté après compactage
- L'utilisateur ne voit rien

---

## Configuration

Config stockée dans `ai_smartness_v2/.ai/config.json`:

```json
{
  "version": "2.0.0",
  "project_name": "MonProjet",
  "language": "fr",
  "settings": {
    "thread_mode": "heavy",
    "auto_capture": true,
    "active_threads_limit": 100
  },
  "llm": {
    "extraction_model": "claude-3-5-haiku-20241022",
    "claude_cli_path": "/usr/local/bin/claude"
  },
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true,
    "require_all_choices": true
  }
}
```

### Différences entre Modes

| Mode | Limite Threads | Cas d'usage |
|------|----------------|-------------|
| Light | 15 | Petits projets |
| Normal | 50 | Projets moyens |
| Heavy | 100 | Grands/complexes projets (blockchain, entreprise) |

**Note**: Le modèle d'extraction est toujours Haiku (économique). Le mode affecte uniquement les limites de threads.

---

## Structure de la Base de Données

```
ai_smartness_v2/.ai/
├── config.json           # Configuration
├── db/
│   ├── threads/          # Fichiers JSON Thread
│   │   └── thread_*.json
│   ├── bridges/          # Fichiers JSON ThinkBridge
│   │   └── bridge_*.json
│   └── synthesis/        # Synthèses de compactage
└── processor.sock        # Socket daemon (quand actif)
```

---

## Hooks Claude Code

| Hook | Script | Fonction |
|------|--------|----------|
| `UserPromptSubmit` | inject.py | Injection de contexte |
| `PostToolUse` | capture.py | Capture automatique |
| `PreCompact` | compact.py | Synthèse à 95% |

---

## Règles GuardCode

| Règle | Description |
|-------|-------------|
| `enforce_plan_mode` | Bloquer les changements de code sans plan validé |
| `warn_quick_solutions` | Rappeler que simple ≠ meilleur |
| `require_all_choices` | Doit présenter toutes les alternatives |

---

## Prérequis

- Python 3.10+
- Claude Code (CLI ou extension VS Code)
- sentence-transformers (pour embeddings locaux)

---

## Dépannage

### Les captures ne fonctionnent pas

Vérifiez les chemins des hooks dans `.claude/settings.json` - ils doivent être des **chemins absolus**.

### Extraction montre "heuristic fallback"

CLI Claude non trouvé. Vérifiez:
```bash
which claude
# Devrait retourner /usr/local/bin/claude ou similaire
```

### Trop de threads

Augmentez la limite dans la config:
```json
"active_threads_limit": 150
```

---

## Licence

MIT

---

**Note**: AI Smartness v2 est une réécriture complète axée sur la simplicité. La métaphore du réseau neuronal est opérationnelle, pas une implémentation neuronale stricte.
