# AI Smartness v6.0

**Couche de méta-cognition pour agents Claude Code avec partage de mémoire inter-agents.**

Un système de mémoire persistante qui transforme Claude Code en un agent capable de maintenir le contexte sémantique sur de longues sessions, de détecter les connexions entre concepts, de partager des connaissances avec d'autres agents, et de reprendre le travail après des semaines/mois comme si vous veniez de faire une pause café.

Compatible avec VS Code & Claude Code CLI.

---

## Philosophie : Partenariat, pas Contrôle

AI Smartness permet un **partenariat** entre vous et votre agent. Il fournit des outils cognitifs - pas des contraintes.

- **GuardCode est consultatif** : Des suggestions, pas de l'application forcée
- **Les premiers contacts comptent** : Laissez les concepts émerger naturellement avec les nouveaux agents
- **La confiance se développe avec le temps** : L'agent apprend vos préférences par la collaboration
- **Autonomie de l'agent** : L'agent gère activement sa propre cognition et sa fenêtre contextuelle
- **Collaboration inter-agents** : Les agents peuvent partager leurs connaissances tout en maintenant l'isolation mémoire

---

## Vision

AI Smartness v6.0 est une **mémoire de travail inspirée des réseaux neuronaux** avec **cognition partagée** :

- **Threads** = Neurones (flux de raisonnement actifs)
- **ThinkBridges** = Synapses (connexions sémantiques entre threads)
- **SharedThreads** = Connaissances publiées (partage inter-agents)
- **Subscriptions** = Connaissances importées d'autres agents
- **InterAgentBridges** = Connexions sémantiques inter-agents (consentement bilatéral)
- **Recall** = Récupération active de la mémoire à la demande
- **Injection Mémoire** = Restauration du contexte à chaque prompt
- **État de Session** = Continuité du travail entre les sessions
- **Profil Utilisateur** = Personnalisation persistante

Le système maintient un **réseau de pensées** où les concepts restent connectés, accessibles et partageables.

---

## Fonctionnalités Clés v6.0

| Fonctionnalité | Description |
|----------------|-------------|
| **Threads** | Unités de travail sémantiques avec titres auto-générés |
| **ThinkBridges** | Connexions automatiques entre threads liés |
| **SharedThreads** | Publication de threads sur le réseau pour partage inter-agents |
| **Subscriptions** | Abonnement aux SharedThreads d'autres agents |
| **InterAgentBridges** | Ponts sémantiques inter-agents (consentement bilatéral, TTL 24h) |
| **Outils MCP** | Outils natifs agent pour la gestion mémoire |
| **Merge/Split** | Topologie mémoire contrôlée par l'agent |
| **Suivi Contexte** | % contexte en temps réel avec throttle adaptatif |
| **État de Session** | Suivi des fichiers modifiés, historique outils, tâches |
| **Profil Utilisateur** | Rôle, préférences, règles contextuelles |
| **Injection en Couches** | Système de contexte à 5 niveaux de priorité |
| **Isolation Mémoire** | Copy-on-share, pull pas push |
| **CLI dans le Prompt** | `ai status` directement dans le prompt |
| **Règles Utilisateur** | Détection et persistance automatiques des préférences |
| **GuardCode** | Système consultatif pour les bonnes pratiques |
| **Synthèse 95%** | Préservation automatique du contexte avant compaction |
| **100% Transparent** | Aucune action utilisateur requise |

---

## Outils MCP Agent (v5.2)

Votre agent a accès aux outils MCP natifs :

### Outils de Base
```
ai_recall(query="authentification")   # Recherche par mot-clé/sujet
ai_help()                             # Auto-documentation agent
ai_status()                           # Status mémoire
```

### Gestion des Threads
```
ai_merge(survivor_id="t1", absorbed_id="t2")   # Fusionner deux threads
ai_split(thread_id="t1")                        # Info split (étape 1)
ai_split(thread_id="t1", confirm=True, ...)    # Exécuter split (étape 2)
ai_unlock(thread_id="t1")                       # Déverrouiller thread
```

### Outils V5 Hybrides
```
ai_suggestions()              # Suggestions d'optimisation proactives
ai_compact(strategy="normal") # Compaction à la demande (gentle/normal/aggressive)
ai_focus(topic="solana")      # Booster priorité injection pour sujets
ai_unfocus()                  # Effacer les topics focus
ai_pin(content="important")   # Capture haute priorité
ai_rate_context(thread_id, useful=True)  # Feedback sur qualité injection
```

### V5.1 Continuité Contextuelle
```
ai_profile(action="view")                          # Voir profil
ai_profile(action="set_role", role="developer")    # Définir rôle
ai_profile(action="add_rule", rule="Toujours utiliser TypeScript")  # Ajouter règle
```

### V5.2 Opérations Batch & Auto-Optimisation
```
ai_merge_batch(operations=[...])   # Fusionner plusieurs threads d'un coup
ai_rename_batch(operations=[...])  # Renommer plusieurs threads d'un coup
ai_cleanup(mode="auto")            # Corriger les threads mal nommés
ai_cleanup(mode="interactive")     # Réviser avant correction
ai_rename(thread_id, new_title)    # Renommer un thread
```
**Compression Proactive :** Le daemon compacte auto quand la pression > 0.80

### V6.0 Cognition Partagée (Mémoire Inter-Agents)
```
ai_share(thread_id)           # Partager un thread sur le réseau
ai_unshare(shared_id)         # Retirer le partage d'un thread
ai_publish(shared_id)         # Publier mise à jour aux abonnés
ai_discover(topics=["rust"])  # Trouver des threads partagés par topics
ai_subscribe(shared_id)       # S'abonner à un thread partagé
ai_unsubscribe(shared_id)     # Se désabonner d'un thread partagé
ai_sync()                     # Synchroniser tous les abonnements périmés
ai_shared_status()            # Afficher le statut de la cognition partagée
```

**Principes d'Isolation Mémoire :**
- **Copy-on-share** : La publication crée un snapshot en lecture seule
- **Pull pas push** : Les abonnés récupèrent explicitement via `ai_sync()`
- **Pas de fuite privée** : Uniquement les IDs SharedThread, jamais les IDs threads privés

---

## Installation

**Plateforme :** Linux / macOS / Windows (via WSL uniquement)

> Les hooks nécessitent des chemins Unix absolus. Les chemins Windows natifs ne sont pas supportés.

### Prérequis (Recommandé)

**sentence-transformers** nécessite PyTorch. Nous recommandons l'installation **avant** le script d'installation pour choisir votre variante :

```bash
# CPU uniquement (plus léger)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers

# OU avec CUDA (plus rapide avec GPU NVIDIA)
pip install torch && pip install sentence-transformers
```

### Lancer l'Installation

```bash
/chemin/vers/ai_smartness-DEV/install.sh /chemin/vers/votre/projet
```

### Ce que fait l'Installateur

| Étape | Action |
|-------|--------|
| 1 | **Sélection langue** (en/fr/es) |
| 2 | **Sélection mode** (MAX/Heavy/Normal/Light → limites threads) |
| 3 | **Migration** depuis `ai_smartness_v2` si présent |
| 4 | **Copie fichiers** vers `projet/ai_smartness/` |
| 5 | **Initialise base de données** (threads, bridges, synthesis) |
| 6 | **Initialise heartbeat.json** (suivi de session) |
| 7 | **Vérifie sentence-transformers** (auto-install si absent) |
| 8 | **Détecte Claude CLI** |
| 9 | **Crée config.json** |
| 10 | **Configure hooks** (4 hooks avec chemins absolus) |
| 11 | **Configure serveur MCP** (outils ai-smartness) |
| 12 | **Configure .gitignore/.claudeignore** |
| 13 | **Installe CLI** dans `~/.local/bin/ai` |
| 14 | **Démarre daemon** (processeur en arrière-plan) |

### Le Daemon

Un daemon en arrière-plan gère :
- Traitement asynchrone des captures
- Extraction LLM pour décisions de threads
- Auto-pruning toutes les 5 minutes

```bash
ai daemon status/start/stop
```

### Prérequis

- Python 3.10+
- Claude Code (CLI ou extension VS Code)
- sentence-transformers (auto-installé ou pré-installé)

---

## Commandes CLI

```bash
# Vue d'ensemble
ai status

# Lister threads
ai threads
ai threads --status active
ai threads --prune

# Voir thread spécifique
ai thread <thread_id>

# Lister bridges
ai bridges
ai bridges --thread <thread_id>

# Recherche sémantique
ai search "authentification"

# Santé système
ai health

# Recalculer embeddings
ai reindex

# Contrôle daemon
ai daemon start
ai daemon stop

# Gestion mode
ai mode heavy
```

### Dans le Prompt (v3.0.0+)

Tapez les commandes CLI directement :
```
Vous: ai status
Claude: [Affiche le statut mémoire]
```

---

## Fonctionnement

### 1. Capture (hook PostToolUse)
```
[Résultat Outil] → [Daemon] → [Extraction LLM] → [Décision Thread]
```

### 2. Gestion Threads
- **NEW_THREAD** : Sujet différent
- **CONTINUE** : Même sujet (similarité > 0.35)
- **FORK** : Sous-sujet
- **REACTIVATE** : Ancien sujet revient (similarité > 0.50)

### 3. Recall Actif (v4.4)
```
ai_recall(query="authentification")
→ Retourne threads, résumés, bridges
```

### 4. Injection Mémoire (UserPromptSubmit)

Nouvelles sessions reçoivent :
- Vue d'ensemble des capabilities
- Dernier thread actif ("hot thread")
- Suggestions de recall

Chaque message reçoit :
- Threads pertinents par similarité
- Règles utilisateur

### 5. Suivi Contexte (v4.3)
- <70% : Mise à jour toutes les 30s
- ≥70% : Mise à jour sur delta 5% uniquement

### 6. Synthèse (PreCompact, 95%)
Synthèse d'état auto-générée avant compaction.

---

## Configuration

```json
{
  "version": "6.0.1",
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100,
    "shared_cognition": {
      "enabled": true,
      "auto_notify_mcp_smartness": true,
      "bridge_proposal_ttl_hours": 24,
      "default_visibility": "network"
    }
  },
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true
  }
}
```

### Modes

| Mode | Limite Threads |
|------|----------------|
| Light | 15 |
| Normal | 50 |
| Heavy | 100 |
| Max | 200 |

---

## Architecture

### Composants

| Composant | Fichier | Rôle |
|-----------|---------|------|
| Daemon | `daemon/processor.py` | Traitement arrière-plan |
| Client | `daemon/client.py` | Communication rapide |
| Hook Capture | `hooks/capture.py` | PostToolUse |
| Hook Injection | `hooks/inject.py` | UserPromptSubmit |
| Hook PreTool | `hooks/pretool.py` | Chemins virtuels .ai/ |
| Handler Recall | `hooks/recall.py` | Recall mémoire + merge/split |
| Hook Compact | `hooks/compact.py` | Synthèse PreCompact |

### Hooks

| Hook | Script | Fonction |
|------|--------|----------|
| `UserPromptSubmit` | inject.py | Commandes CLI + injection mémoire |
| `PreToolUse` | pretool.py | Chemins virtuels .ai/ |
| `PostToolUse` | capture.py | Capture threads |
| `PreCompact` | compact.py | Génération synthèse |

---

## Dépannage

### Daemon non démarré
```bash
ai daemon start
```

### L'agent n'utilise pas recall
Normal pour les nouveaux agents. Ils doivent découvrir leurs outils :
1. Mentionnez que `ai_recall()` existe
2. Pointez vers `ai_help()`
3. Faites confiance au processus d'apprentissage

### Scores de similarité faibles
```bash
pip install sentence-transformers
ai daemon stop && ai daemon start
ai reindex
```

---

## Structure Base de Données

```
ai_smartness/.ai/
├── config.json
├── heartbeat.json        # Suivi session, % contexte
├── user_rules.json
├── processor.pid
├── processor.sock
├── processor.log
├── inject.log
└── db/
    ├── threads/
    ├── bridges/
    ├── synthesis/
    └── shared/           # v6.0 Cognition Partagée
        ├── published/    # SharedThreads de cet agent
        ├── subscriptions/# Abonnements aux SharedThreads d'autres agents
        ├── cross_bridges/# InterAgentBridges (consentement bilatéral)
        └── proposals/    # Propositions de bridges en attente
            ├── outgoing/
            └── incoming/
```

---

## Licence

MIT

---

**Note** : AI Smartness est conçu pour être invisible. La meilleure indication qu'il fonctionne est que votre agent devient un meilleur collaborateur avec le temps - pas que rien ne se passe jamais mal.
