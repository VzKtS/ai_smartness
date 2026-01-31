# AI Smartness v3 - Guide Utilisateur

## Démarrage Rapide

1. **Installez** dans votre projet :
   ```bash
   /chemin/vers/ai_smartness_v2-DEV/install.sh /chemin/vers/votre/projet
   ```

2. **Travaillez normalement** - le système capture tout automatiquement

3. **Vérifiez le status** à tout moment :
   ```bash
   ai status
   ```

C'est tout. Le système est 100% transparent.

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

Sortie :
```
=== AI Smartness Health ===
Threads: 158 (100 active, 58 suspended)
Bridges: 3374
Continuation rate: 23.4%
Embedding coverage: 100.0%
Daemon: Running (PID 12345)
```

**Métriques clés :**
- **Continuation rate** : % de threads avec >1 message (plus c'est haut, mieux c'est)
- **Embedding coverage** : % de threads avec embeddings valides (devrait être 100%)
- **Daemon** : Devrait être "Running"

### `ai reindex`

Recalcule tous les embeddings :
```bash
ai reindex           # Standard
ai reindex --verbose # Avec détails de progression
```

À utiliser après :
- Installation de sentence-transformers
- Mise à jour d'AI Smartness
- Si l'embedding coverage est < 100%

### `ai daemon`

Contrôle du daemon en arrière-plan :
```bash
ai daemon           # Affiche le status (défaut)
ai daemon status    # Affiche le status
ai daemon start     # Démarre le daemon
ai daemon stop      # Arrête le daemon
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
Memory Retriever trouve les threads pertinents (par similarité)
         ↓
Réactivation automatique des threads suspendus si pertinents
         ↓
Chaîne de contexte construite :
  - Titre + résumé du thread courant
  - Threads liés (via bridges)
  - Règles utilisateur
         ↓
Injecté comme <system-reminder> invisible
         ↓
Claude reçoit votre message + contexte
```

### Réactivation Automatique des Threads

Quand vous mentionnez un sujet lié à un thread suspendu, le système peut automatiquement le réactiver :

| Similarité | Action |
|------------|--------|
| > 0.35 | Réactivation auto (haute confiance) |
| 0.15 - 0.35 | LLM Haiku décide (zone borderline) |
| < 0.15 | Pas de réactivation |

**Exemple :** Si vous avez travaillé sur "système de mémoire IA" hier (maintenant suspendu), et aujourd'hui vous demandez :
> "parle-moi de la couche de meta cognition"

Le système :
1. Calcule la similarité avec "système de mémoire IA" (borderline: 0.28)
2. Consulte Haiku : "Ce message concerne-t-il ce thread ?"
3. Haiku confirme la relation sémantique
4. Réactive le thread
5. Injecte le contexte dans votre conversation

**Libération de Slots :** Si vous êtes au maximum de threads actifs (ex: 100/100), le système suspend automatiquement le thread actif le moins important pour faire de la place au thread réactivé.

### Ce qui est Injecté

Exemple d'injection (invisible pour vous) :
```xml
<system-reminder>
AI Smartness Memory Context:

Current thread: "Authentification JWT"
Summary: Implémentation de rotation de refresh tokens avec stockage Redis.

Related threads:
- "Schéma Base de Données" - Tables utilisateurs et sessions
- "Audit Sécurité" - Politiques d'expiration des tokens

User rules:
- toujours faire un plan avant l'implémentation
- utiliser le mode strict TypeScript
</system-reminder>

Votre message réel ici...
```

---

## Bonnes Pratiques

### Laissez le Système Travailler

N'essayez pas d'"aider" le système :
- Travaillez normalement
- Le système capture tout automatiquement
- Les threads se forment naturellement selon votre travail

### Exprimez vos Préférences

Dites à l'agent vos règles :
- "rappelle-toi : je préfère la programmation fonctionnelle"
- "règle : toujours ajouter des tests pour les nouvelles fonctions"
- "jamais utiliser any comme type"

Elles sont stockées et appliquées à toutes les sessions futures.

### Vérifiez la Santé Régulièrement

```bash
ai health
```

- Taux de continuation < 10% ? Vérifiez les embeddings
- Daemon arrêté ? Lancez `ai daemon start`
- Couverture embeddings < 100% ? Lancez `ai reindex`

### Reprise de Session

Quand vous démarrez une nouvelle session :
1. La mémoire est injectée automatiquement
2. Vérifiez le status : `ai status`
3. Votre agent "se souvient" du contexte précédent

---

## Configuration

### Emplacement

`ai_smartness_v2/.ai/config.json`

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

Le mode **MAX** est recommandé pour :
- Projets avec de nombreux composants interdépendants
- Sessions de travail très longues (15+ heures)
- Cas où la perte de mémoire serait critique

---

## Dépannage

### "Daemon not running"

```bash
ai daemon start
```

Si échec, vérifiez les logs :
```bash
cat ai_smartness_v2/.ai/daemon_stderr.log
```

### "Heuristic fallback" dans les titres

CLI Claude non trouvé. Vérifiez :
```bash
which claude
```

Mettez à jour le chemin dans config si nécessaire.

### Taux de continuation bas

Les threads ne se consolident pas ? Vérifiez :
1. sentence-transformers est-il installé ?
   ```bash
   python3 -c "import sentence_transformers; print('OK')"
   ```
2. Si non : `pip install sentence-transformers`
3. Redémarrez le daemon : `ai daemon stop && ai daemon start`
4. Réindexez : `ai reindex`

### Mémoire non injectée

Vérifiez les logs d'injection :
```bash
tail -20 ai_smartness_v2/.ai/inject.log
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
| `.ai/processor.pid` | ID du processus daemon |
| `.ai/processor.sock` | Socket du daemon |
| `.ai/processor.log` | Logs du daemon |
| `.ai/inject.log` | Logs d'injection |
| `.ai/db/threads/*.json` | Données des threads |
| `.ai/db/bridges/*.json` | Données des bridges |
| `.ai/db/synthesis/*.json` | Synthèses de compaction |

---

## Ce qu'AI Smartness NE FAIT PAS

| Fonctionnalité | Pourquoi Non |
|----------------|--------------|
| Requiert une action utilisateur | 100% transparent |
| Stocke le contenu du code | Uniquement la sémantique, pas le code complet |
| Envoie des données à l'extérieur | 100% local |
| Modifie votre code | Système de mémoire en lecture seule |
| Requiert une configuration | Fonctionne out of the box |

---

## Support

Si vous rencontrez des problèmes :
1. Lancez `ai health` pour diagnostiquer
2. Vérifiez les logs dans `ai_smartness_v2/.ai/`
3. Vérifiez les hooks dans `.claude/settings.json`
4. Essayez `ai daemon stop && ai daemon start`
