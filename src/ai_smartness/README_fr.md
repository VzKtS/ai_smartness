# AI Smartness v3

**Couche de méta-cognition pour agents Claude Code.**

Un système de mémoire persistante qui transforme Claude Code en un agent capable de maintenir le contexte sémantique sur de longues sessions, de détecter les connexions entre concepts, et de reprendre le travail après des semaines/mois comme si vous veniez de faire une pause café.

Compatible avec VS Code & Claude Code CLI.

**Nouveau en v3.0.0** : Commandes CLI directement dans le prompt ! Tapez `ai status`, `ai threads`, etc. dans votre prompt et obtenez les résultats automatiquement injectés.

---

## Vision

AI Smartness est une **mémoire de travail inspirée des réseaux neuronaux** :

- **Threads** = Neurones (flux de raisonnement actifs)
- **ThinkBridges** = Synapses (connexions sémantiques entre threads)
- **Gossip** = Propagation du signal à travers le réseau
- **Injection Mémoire** = Restauration du contexte à chaque prompt

Le système maintient un **réseau de pensées** où les concepts restent connectés et accessibles, évitant la perte de contexte typique des interactions LLM classiques.

---

## Fonctionnalités Clés

| Fonctionnalité | Description |
|----------------|-------------|
| **Threads** | Unités de travail sémantiques avec titres auto-générés |
| **ThinkBridges** | Connexions automatiques entre threads liés |
| **Propagation Gossip** | Les bridges se propagent quand les concepts évoluent |
| **Injection Mémoire** | Contexte pertinent injecté dans chaque prompt |
| **Règles Utilisateur** | Détection et persistance automatiques de vos préférences |
| **GuardCode** | Application du mode plan, protection contre la dérive |
| **Synthèse 95%** | Préservation automatique du contexte avant compaction |
| **Architecture Daemon** | Traitement en arrière-plan pour réponse rapide |
| **100% Transparent** | Aucune action utilisateur requise |

---

## Installation

```bash
# Clonez ou copiez ai_smartness-DEV sur votre machine
# Puis lancez l'installation dans votre projet cible :
/chemin/vers/ai_smartness-DEV/install.sh /chemin/vers/votre/projet
```

### Ce que fait l'installateur

1. **Sélection de langue** : Anglais, Français ou Espagnol
2. **Sélection du mode** : Heavy, Normal ou Light (affecte les limites de threads)
3. **Installe sentence-transformers** (si pas déjà installé)
4. **Détecte le CLI Claude** pour l'extraction LLM
5. **Copie les fichiers** dans `votre_projet/ai_smartness/`
6. **Configure les hooks** avec chemins absolus dans `.claude/settings.json`
7. **Initialise la base de données** dans `ai_smartness/.ai/db/`
8. **Installe le CLI** dans `~/.local/bin/ai`

### Prérequis

- Python 3.10+
- Claude Code (CLI ou extension VS Code)
- pip (pour l'installation automatique de sentence-transformers)

L'installateur gère les dépendances automatiquement. Si sentence-transformers échoue, le système utilise TF-IDF (fonctionnel mais moins précis).

---

## Commandes CLI

Après installation, utilisez la commande `ai` depuis votre répertoire projet :

```bash
# Vue d'ensemble
ai status

# Lister les threads
ai threads
ai threads --status active
ai threads --status suspended
ai threads --limit 20

# Voir un thread spécifique
ai thread <thread_id>

# Lister les bridges
ai bridges
ai bridges --thread <thread_id>

# Recherche sémantique
ai search "authentification"

# Vérification de santé
ai health

# Recalculer les embeddings
ai reindex

# Contrôle du daemon
ai daemon           # Afficher le statut
ai daemon status    # Afficher le statut
ai daemon start     # Démarrer le daemon
ai daemon stop      # Arrêter le daemon
```

---

## Fonctionnement

### 1. Capture (hook PostToolUse)

Chaque résultat d'outil (Read, Write, Task, etc.) est envoyé au daemon :
```
[Résultat Outil] → [Daemon] → [Filtre Bruit] → [Extraction LLM] → [Décision Thread]
```

### 2. Gestion des Threads

Le système décide pour chaque entrée :
- **NEW_THREAD** : Sujet différent → créer un nouveau thread
- **CONTINUE** : Même sujet → ajouter au thread actif (similarité > 0.35)
- **FORK** : Sous-sujet → créer un thread enfant
- **REACTIVATE** : Ancien sujet revient → réveiller le thread suspendu (similarité > 0.50)

### 3. Propagation Gossip

Quand un thread change :
```
Thread A modifié → Recalcul de l'embedding
                 → Pour chaque thread B connecté
                 → Si similarité élevée → propager les bridges
```

### 4. Injection Mémoire (hook UserPromptSubmit)

Avant chaque prompt utilisateur, le contexte pertinent est injecté :
```xml
<system-reminder>
AI Smartness Memory Context:

Current thread: "Système d'Authentification"
Summary: Implémentation d'auth JWT avec refresh tokens...

Related threads:
- "Schéma Base de Données" - Design tables utilisateurs
- "Endpoints API" - Routes d'authentification

User rules:
- toujours faire un plan avant l'implémentation
</system-reminder>
```

L'utilisateur ne voit rien - c'est invisible pour vous mais visible pour l'agent.

### 5. Détection des Règles Utilisateur

Le système détecte et stocke automatiquement vos préférences :
- "rappelle-toi : toujours utiliser TypeScript"
- "règle : pas de console.log en production"
- "toujours faire un plan avant l'implémentation"
- "jamais de commit direct sur main"

Les règles sont stockées dans `ai_smartness/.ai/user_rules.json` et injectées dans chaque prompt.

### 6. Synthèse (hook PreCompact)

À 95% de la fenêtre de contexte :
- Le LLM génère une synthèse de l'état actuel
- Décisions, questions ouvertes, threads actifs
- Injecté après compaction
- L'utilisateur ne voit rien

---

## Configuration

Config stockée dans `ai_smartness/.ai/config.json` :

```json
{
  "version": "2.2.0",
  "project_name": "MonProjet",
  "language": "fr",
  "settings": {
    "thread_mode": "heavy",
    "auto_capture": true,
    "active_threads_limit": 100
  },
  "llm": {
    "extraction_model": "claude-3-5-haiku-20241022",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
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

| Mode | Limite Threads | Cas d'Usage |
|------|----------------|-------------|
| Light | 15 | Petits projets |
| Normal | 50 | Projets moyens |
| Heavy | 100 | Grands projets complexes |

### Seuils de Similarité

| Contexte | Seuil | Description |
|----------|-------|-------------|
| Continuation thread actif | 0.35 | Minimum pour continuer un thread |
| Réactivation thread suspendu | 0.50 | Minimum pour réveiller un thread |
| Boost topic | +0.15 | Bonus pour correspondance exacte de topic |

---

## Structure Base de Données

```
ai_smartness/.ai/
├── config.json           # Configuration
├── user_rules.json       # Règles utilisateur
├── processor.pid         # PID du daemon
├── processor.sock        # Socket du daemon
├── processor.log         # Logs du daemon
├── inject.log            # Logs d'injection
└── db/
    ├── threads/          # Fichiers JSON des threads
    ├── bridges/          # Fichiers JSON des bridges
    └── synthesis/        # Synthèses de compaction
```

---

## Dépannage

### Daemon non démarré

```bash
ai daemon status
# Si arrêté :
ai daemon start
```

### Captures non fonctionnelles

Vérifiez les chemins des hooks dans `.claude/settings.json` - ils doivent être **absolus**.

### "Heuristic fallback" dans les titres

CLI Claude non trouvé :
```bash
which claude
# Mettez à jour le chemin dans config.json si nécessaire
```

### Scores de similarité faibles / Mauvaise mémoire

sentence-transformers non installé :
```bash
pip install sentence-transformers
ai daemon stop
ai daemon start
ai reindex
```

### Taux de continuation faible

Vérifiez avec `ai health`. Si < 10% :
1. Vérifiez que sentence-transformers est installé
2. Lancez `ai reindex`
3. Consultez `ai_smartness/.ai/processor.log`

---

## Architecture

### Composants

| Composant | Fichier | Rôle |
|-----------|---------|------|
| Daemon | `daemon/processor.py` | Traitement en arrière-plan |
| Client | `daemon/client.py` | Communication rapide avec daemon |
| Hook Capture | `hooks/capture.py` | Capture PostToolUse |
| Hook Injection | `hooks/inject.py` | Injection UserPromptSubmit |
| Hook Compact | `hooks/compact.py` | Synthèse PreCompact |
| Memory Retriever | `intelligence/memory_retriever.py` | Récupération du contexte |
| Thread Manager | `intelligence/thread_manager.py` | Cycle de vie des threads |
| Gossip | `intelligence/gossip.py` | Propagation des bridges |
| Embeddings | `processing/embeddings.py` | Embeddings vectoriels |

---

## Licence

MIT

---

**Note** : AI Smartness est conçu pour être invisible. La meilleure indication qu'il fonctionne est que votre agent "se souvient" du contexte entre les sessions sans que vous fassiez quoi que ce soit de spécial.
