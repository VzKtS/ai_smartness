# AI Smartness v4 - Guide Utilisateur

## Démarrage Rapide

**Plateforme :** Linux / macOS / Windows (WSL requis)

> Le système de hooks nécessite des chemins Unix absolus. Sur Windows, utilisez WSL (Windows Subsystem for Linux).

### 1. Pré-installer les Dépendances (Recommandé)

sentence-transformers nécessite PyTorch. Installez **avant** le script d'installation pour choisir CPU ou GPU :

```bash
# CPU uniquement (pas de GPU requis, plus léger)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers

# OU avec support CUDA (plus rapide avec GPU NVIDIA)
pip install torch && pip install sentence-transformers
```

Si vous sautez cette étape, l'installateur installera automatiquement la version par défaut (CPU).

### 2. Lancer l'Installation

```bash
/chemin/vers/ai_smartness-DEV/install.sh /chemin/vers/votre/projet
```

L'installateur va :
- Demander la langue (en/fr/es) et le mode (MAX/Heavy/Normal/Light)
- Copier les fichiers, configurer les hooks, démarrer le daemon en arrière-plan
- Installer la commande CLI `ai`

### 3. Travaillez Normalement

Le système capture tout automatiquement. Vérifiez le status à tout moment :
```bash
ai status
```
Ou tapez `ai status` directement dans votre prompt !

C'est tout. Le système est 100% transparent.

---

## Comprendre le Modèle de Partenariat

AI Smartness n'est pas un "système de contrôle" pour votre agent - c'est une **couche d'amélioration cognitive** qui permet un vrai partenariat.

### Qu'est-ce qu'un Bon Partenariat ?

| Approche Traditionnelle | Approche Partenariat |
|------------------------|---------------------|
| Règles rigides imposées | Guidelines comprises |
| Prévenir toutes les erreurs | Apprendre du contexte |
| Contrôler le comportement | Activer les capacités |
| Méfiance par défaut | Confiance par l'expérience |

### Votre Rôle en tant qu'Utilisateur

Vous n'êtes pas un "superviseur" corrigeant un système peu fiable. Vous êtes un **partenaire** travaillant avec un agent intelligent qui :

- A son propre système de mémoire
- Peut gérer son propre contexte
- Apprend vos préférences au fil du temps
- Fait des choix basés sur le contexte

### Premières Sessions avec un Nouvel Agent

Les premières sessions sont cruciales. Pendant ce temps :

1. **Laissez l'agent explorer** - Ne restreignez pas immédiatement
2. **Exprimez vos préférences naturellement** - "Je préfère X" plutôt que "Tu dois toujours X"
3. **Observez ce qui émerge** - L'agent peut développer des habitudes utiles
4. **Guidez en douceur** - Redirigez plutôt qu'interdire

L'objectif est un agent qui *comprend* les bonnes pratiques, pas un qui suit aveuglément des règles.

---

## Concepts Clés

### Threads

Un **Thread** est une unité de travail sémantique représentant un sujet ou une tâche.

| Status | Description |
|--------|-------------|
| `active` | En cours de travail |
| `suspended` | En pause, peut être réactivé |
| `archived` | Terminé ou dormant |

Les threads contiennent :
- **Titre** : Titre sémantique auto-généré
- **Messages** : Historique des interactions
- **Résumé** : Résumé auto-généré
- **Topics** : Concepts clés extraits
- **Embedding** : Vecteur pour recherche par similarité

### ThinkBridges

Un **ThinkBridge** est une connexion sémantique entre deux threads.

| Type | Signification |
|------|---------------|
| `extends` | A étend/raffine B |
| `depends` | A dépend de B |
| `contradicts` | A et B sont en tension |
| `replaces` | A remplace B |
| `child_of` | A est un sous-sujet de B |

Les bridges sont créés automatiquement quand le système détecte une similarité sémantique.

### Règles Utilisateur

Le système détecte et mémorise vos préférences. Dites des choses comme :
- "rappelle-toi : toujours utiliser TypeScript"
- "règle : pas de commit direct sur main"
- "toujours faire un plan avant l'implémentation"
- "jamais de console.log en production"

Ces règles sont stockées de façon permanente et injectées dans chaque prompt.

---

## Outils MCP Agent (v4.4)

Votre agent a accès aux outils MCP natifs pour la gestion de la mémoire :

### Recall Actif

```
ai_recall(query="authentification")
```

Recherche dans la mémoire par mot-clé ou sujet. Retourne les threads correspondants avec résumés, topics et bridges liés.

**Exemples :**
- `ai_recall(query="solana")` - Tout ce qui concerne Solana
- `ai_recall(query="hooks")` - Mémoire sur les hooks
- `ai_recall(query="authentification")` - Travaux liés à l'auth
- `ai_recall(query="thread_abc123")` - Thread spécifique par ID

### Fusionner des Threads

```
ai_merge(survivor_id="t1", absorbed_id="t2")
```

Combine deux threads liés pour libérer du contexte. Le survivor absorbe :
- Tous les messages (triés par timestamp)
- Topics et tags (union)
- Boost de weight (+0.1)

Le thread absorbé est archivé avec le tag `merged_into:<survivor_id>`.

**Note :** Les threads split-locked ne peuvent pas être absorbés.

### Diviser des Threads

Workflow en deux étapes quand un thread a dérivé vers plusieurs sujets :

**Étape 1 - Obtenir les infos du thread :**
```
ai_split(thread_id="abc")
```
Retourne la liste des messages avec leurs IDs.

**Étape 2 - Confirmer le split :**
```
ai_split(thread_id="abc", confirm=True, titles=["T1", "T2"], message_groups=[["m1", "m2"], ["m3", "m4"]])
```

**Modes de verrouillage :**
| Mode | Description |
|------|-------------|
| `compaction` | Auto-déverrouillage au prochain compactage (défaut) |
| `agent_release` | Déverrouillage manuel via `ai_unlock()` |
| `force` | Jamais de déverrouillage automatique |

### Déverrouiller des Threads

```
ai_unlock(thread_id="abc")
```

Retire la protection split-lock, permettant au thread d'être fusionné.

### Aide & Status

```
ai_help()    # Documentation complète de l'agent
ai_status()  # Status mémoire (threads, bridges, % contexte)
```

Utile quand l'agent doit se rappeler ses capacités ou vérifier l'état actuel de la mémoire.

---

## CLI dans le Prompt (v3.0.0+)

Tapez les commandes CLI directement dans votre prompt et elles seront exécutées automatiquement :

```
Vous: ai status
Claude: [Affiche le status mémoire depuis le CLI]

Vous: ai threads
Claude: [Liste les threads actifs]

Vous: ai search authentication
Claude: [Affiche les résultats de recherche pour "authentication"]
```

**Commandes supportées :** `ai status`, `ai threads`, `ai thread <id>`, `ai bridges`, `ai search <query>`, `ai health`, `ai daemon`, `ai mode`, `ai help`

---

## Référence CLI

### `ai status`

Affiche la vue d'ensemble globale :
```
=== AI Smartness Status ===
Project: MonProjet

Threads: 45 total
  Active:    12
  Suspended: 33
  Archived:  0

Bridges: 234 connections

Last activity: 2026-01-29 15:30:22
Current thread: "Système d'Authentification"
```

### `ai threads`

Liste les threads avec filtrage :
```bash
ai threads                    # Threads actifs (défaut)
ai threads --status active    # Actifs uniquement
ai threads --status suspended # Suspendus uniquement
ai threads --status all       # Tous les threads
ai threads --limit 20         # Limiter à 20 résultats
ai threads --prune            # Appliquer decay et suspendre les threads faibles
```

### `ai thread <id>`

Affiche les détails d'un thread :
```bash
ai thread abc123
```

### `ai bridges`

Liste les connexions sémantiques :
```bash
ai bridges                    # Tous les bridges
ai bridges --thread abc123    # Bridges pour un thread spécifique
ai bridges --limit 50         # Limiter les résultats
ai bridges --prune            # Appliquer decay et supprimer bridges morts
```

### `ai search`

Recherche sémantique dans tous les threads :
```bash
ai search "authentification"
ai search "migration base de données" --limit 10
```

### `ai health`

Vérification de santé du système :
```bash
ai health
```

### `ai daemon`

Contrôle du daemon en arrière-plan :
```bash
ai daemon           # Affiche le status (défaut)
ai daemon status    # Affiche le status
ai daemon start     # Démarre le daemon
ai daemon stop      # Arrête le daemon
```

### `ai mode`

Voir ou changer le mode de fonctionnement :
```bash
ai mode             # Affiche le mode actuel
ai mode light       # Passe en mode light (15 threads)
ai mode normal      # Passe en mode normal (50 threads)
ai mode heavy       # Passe en mode heavy (100 threads)
ai mode max         # Passe en mode max (200 threads)
```

---

## Comment Fonctionne la Mémoire

### Flux de Capture

```
Vous utilisez un outil (Read, Write, etc.)
         ↓
Le hook PostToolUse se déclenche
         ↓
Contenu envoyé au daemon (rapide, non-bloquant)
         ↓
Le daemon extrait la sémantique (LLM)
         ↓
Décision thread : NEW / CONTINUE / FORK / REACTIVATE
         ↓
Thread mis à jour, bridges recalculés
```

### Flux d'Injection

```
Vous tapez un message
         ↓
Le hook UserPromptSubmit se déclenche
         ↓
Vérification : Est-ce une nouvelle session ?
         ↓
Si NOUVELLE SESSION :
  - Injecter vue d'ensemble des capacités
  - Afficher le dernier thread actif ("hot thread")
  - Suggérer recall si le message correspond aux topics
         ↓
Toujours :
  - Memory Retriever trouve les threads pertinents (par similarité)
  - Réactivation auto des threads suspendus si pertinents
         ↓
Chaîne de contexte construite et injectée
         ↓
Claude reçoit votre message + contexte
```

### Suivi de Contexte (v4.3)

Monitoring du contexte en temps réel avec throttle adaptatif :

| Contexte % | Comportement |
|------------|--------------|
| < 70% | Mise à jour toutes les 30 secondes |
| ≥ 70% | Mise à jour uniquement sur delta de 5% |

Cela évite les appels API inutiles tout en gardant l'agent conscient de la pression sur le contexte.

### Réactivation Automatique des Threads

Quand vous mentionnez un sujet lié à un thread suspendu, le système peut automatiquement le réactiver :

| Similarité | Action |
|------------|--------|
| > 0.35 | Réactivation auto (haute confiance) |
| 0.15 - 0.35 | LLM Haiku décide (zone borderline) |
| < 0.15 | Pas de réactivation |

### Système de Decay Neural

Les threads et bridges utilisent un système de poids inspiré des réseaux neuronaux (apprentissage Hebbien) :

| Action | Effet sur le Weight |
|--------|---------------------|
| Nouveau thread | Démarre à 1.0 |
| Fork thread | Hérite du weight du parent |
| Chaque utilisation (message) | +0.1 boost (max 1.0) |
| Decay temporel | Divise par 2 tous les 7 jours |
| En-dessous de 0.1 | Thread auto-suspendu |
| En-dessous de 0.05 | Bridge auto-supprimé |

---

## Bonnes Pratiques

### Laissez le Système Travailler

N'essayez pas d'"aider" le système :
- Travaillez normalement
- Le système capture tout automatiquement
- Les threads se forment naturellement selon votre travail

### Exprimez vos Préférences Naturellement

Au lieu de règles rigides, exprimez des préférences :
- "Je préfère la programmation fonctionnelle"
- "On ajoute toujours des tests pour les nouvelles fonctions"
- "Je n'aime pas utiliser any comme type"

Elles sont stockées et appliquées naturellement.

### Faites Confiance au Processus d'Apprentissage

Les premières sessions enseignent les fondamentaux. Avec le temps :
- L'agent apprend vos patterns
- La gestion du contexte s'améliore
- Le partenariat s'approfondit

### À Propos de GuardCode

GuardCode est un **conseiller**, pas un exécuteur. Il :
- Suggère de planifier avant l'implémentation
- Rappelle les bonnes pratiques
- Encourage à présenter les options

Il ne fait **pas** :
- Garantir un comportement spécifique
- Prévenir toutes les erreurs
- Outrepasser le jugement de l'agent

Si votre agent fait un choix avec lequel vous n'êtes pas d'accord, discutez-en. C'est comme ça que les partenariats fonctionnent.

### Gestion Proactive du Contexte

Un agent mature devrait rarement atteindre le compactage. Encouragez cela en :
1. Enseignant merge/split tôt
2. Appréciant quand l'agent gère le contexte
3. Faisant confiance aux décisions de l'agent sur ce qu'il faut garder/archiver

---

## Configuration

### Emplacement

`ai_smartness/.ai/config.json`

### Paramètres Clés

```json
{
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100
  },
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true,
    "require_all_choices": true
  }
}
```

### Comparaison des Modes

| Mode | Limite Threads | Idéal Pour |
|------|----------------|------------|
| MAX | 200 | Projets complexes, sessions 15+ heures |
| heavy | 100 | Grandes codebases, projets longs |
| normal | 50 | Projets moyens |
| light | 15 | Petits scripts, tâches rapides |

---

## Dépannage

### "Daemon not running"

```bash
ai daemon start
```

Si échec, vérifiez les logs :
```bash
cat ai_smartness/.ai/daemon_stderr.log
```

### L'agent n'utilise pas recall

C'est normal pour les nouveaux agents. Ils doivent découvrir leurs outils :
1. Vous pouvez le mentionner : "Tu peux utiliser `ai_recall()` pour chercher dans ta mémoire"
2. Pointez vers `ai_help()`
3. Faites confiance au processus d'apprentissage

### L'agent compacte trop

L'agent devrait apprendre à gérer le contexte proactivement. Si le compactage arrive fréquemment :
1. Discutez de la gestion du contexte avec l'agent
2. Encouragez l'utilisation de merge/split
3. Vérifiez si le mode est approprié (peut-être passer à MAX)

### Mémoire non injectée

Vérifiez les logs d'injection :
```bash
tail -20 ai_smartness/.ai/inject.log
```

Devrait afficher des lignes comme :
```
[2026-01-29 15:30:22] Injected: 450 chars (380 memory) for: Comment faire...
```

### Hooks qui ne se déclenchent pas

Vérifiez `.claude/settings.json` :
- Les chemins doivent être **absolus**
- Python3 doit être dans le PATH

---

## Référence des Fichiers

| Fichier | But |
|---------|-----|
| `.ai/config.json` | Configuration |
| `.ai/user_rules.json` | Vos règles stockées |
| `.ai/heartbeat.json` | Suivi session, % contexte |
| `.ai/processor.pid` | ID du processus daemon |
| `.ai/processor.sock` | Socket du daemon |
| `.ai/processor.log` | Logs du daemon |
| `.ai/inject.log` | Logs d'injection |
| `.ai/db/threads/*.json` | Données des threads |
| `.ai/db/bridges/*.json` | Données des bridges |
| `.ai/db/synthesis/*.json` | Synthèses de compaction |

---

## Le Voyage du Partenariat

| Phase | À Quoi S'attendre |
|-------|-------------------|
| **Sessions 1-3** | L'agent découvre ses outils, construit sa mémoire initiale |
| **Sessions 4-10** | Des patterns émergent, les préférences se solidifient |
| **Sessions 10+** | Partenariat mature, gestion proactive du contexte |
| **Long terme** | L'agent compacte rarement, gère la mémoire expertement |

La meilleure indication qu'AI Smartness fonctionne n'est pas que rien ne va mal - c'est que votre agent devient un meilleur collaborateur au fil du temps.

---

## Ce qu'AI Smartness NE FAIT PAS

| Fonctionnalité | Pourquoi Non |
|----------------|--------------|
| Garantir le comportement | Consultatif, pas imposé |
| Requiert une action utilisateur | 100% transparent |
| Stocke le contenu du code | Uniquement la sémantique, pas le code complet |
| Envoie des données à l'extérieur | 100% local |
| Modifie votre code | Système de mémoire en lecture seule |
| Remplace votre jugement | Partenariat, pas remplacement |

---

## Support

Si vous rencontrez des problèmes :
1. Lancez `ai health` pour diagnostiquer
2. Vérifiez les logs dans `ai_smartness/.ai/`
3. Vérifiez les hooks dans `.claude/settings.json`
4. Essayez `ai daemon stop && ai daemon start`

Rappelez-vous : Beaucoup de "problèmes" sont en fait l'agent en train d'apprendre. Laissez-lui du temps avant de troubleshooter.
