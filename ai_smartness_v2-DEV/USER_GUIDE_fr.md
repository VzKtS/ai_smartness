# AI Smartness v2 - Guide Utilisateur

## Aperçu

AI Smartness v2 est un système de mémoire persistante pour Claude Code. Il capture automatiquement votre contexte de travail, l'organise en threads sémantiques, et maintient les connexions entre concepts liés.

**Principe clé**: 100% transparent - vous n'avez rien de spécial à faire. Travaillez normalement.

---

## Concepts Clés

### Threads

Un **Thread** est une unité de travail sémantique représentant un sujet ou une tâche:

| Status | Description |
|--------|-------------|
| `active` | En cours de travail |
| `suspended` | En pause, peut être réactivé |
| `archived` | Terminé ou dormant |

Les threads contiennent:
- **Titre**: Titre sémantique généré par LLM
- **Messages**: Historique des interactions
- **Résumé**: Résumé généré par LLM
- **Embedding**: Vecteur pour recherche par similarité

### ThinkBridges

Un **ThinkBridge** est une connexion sémantique entre deux threads.

Types de bridges:
| Type | Signification |
|------|---------------|
| `extends` | A étend/raffine B |
| `depends` | A dépend de B |
| `contradicts` | A et B sont en tension |
| `replaces` | A remplace B |
| `child_of` | A est un sous-sujet de B |

Les bridges sont créés automatiquement quand le système détecte une similarité sémantique entre threads.

### Propagation Gossip

Quand un thread change, ses connexions **se propagent** dans le réseau:
- Thread A modifié → ses bridges sont évalués
- Si forte similarité avec threads connectés → nouveaux bridges créés
- Crée une "toile de connaissances" qui grandit organiquement

---

## Comment ça Marche (En coulisses)

### 1. Capture

Chaque résultat d'outil (Read, Write, Task, Bash, etc.) est capturé et traité:
1. **Filtre bruit**: Supprime les tags IDE, numéros de ligne, formatage
2. **Extraction LLM**: Extrait intention, sujets, questions
3. **Décision thread**: Nouveau thread? Continuer existant? Fork?

### 2. Gestion des Threads

Le LLM décide quoi faire avec chaque input:

| Décision | Quand |
|----------|-------|
| `NEW_THREAD` | Sujet différent des threads actifs |
| `CONTINUE` | Même sujet que le thread actif |
| `FORK` | Sous-sujet du thread actif |
| `REACTIVATE` | Ancien sujet qui revient |

### 3. Injection de Contexte

Avant chacun de vos prompts, du contexte invisible est injecté:
- Info du thread actif
- Décisions récentes
- Rappels GuardCode

Vous ne voyez jamais ça, mais ça aide l'agent à maintenir la cohérence.

### 4. Synthèse à 95%

Quand la fenêtre contextuelle se remplit à 95%:
1. Le LLM génère une synthèse de l'état actuel
2. Décisions clés, questions ouvertes, travail actif
3. La synthèse est injectée après compactage
4. Vous ne voyez rien - le contexte est préservé

---

## Commandes CLI

### Status

```bash
# Aperçu global
python3 ai_smartness_v2/cli/main.py status
```

Affiche:
- Nombre de threads par status
- Nombre de bridges
- Dernière activité
- Titre du thread actif

### Threads

```bash
# Lister tous les threads
python3 ai_smartness_v2/cli/main.py threads

# Filtrer par status
python3 ai_smartness_v2/cli/main.py threads --status active
python3 ai_smartness_v2/cli/main.py threads --status suspended
python3 ai_smartness_v2/cli/main.py threads --status archived

# Limiter les résultats
python3 ai_smartness_v2/cli/main.py threads --limit 10

# Voir un thread spécifique
python3 ai_smartness_v2/cli/main.py thread thread_20260128_143022_abc123
```

### Bridges

```bash
# Lister tous les bridges
python3 ai_smartness_v2/cli/main.py bridges

# Filtrer par thread
python3 ai_smartness_v2/cli/main.py bridges --thread thread_20260128_143022

# Limiter les résultats
python3 ai_smartness_v2/cli/main.py bridges --limit 20
```

### Recherche

```bash
# Recherche sémantique dans les threads
python3 ai_smartness_v2/cli/main.py search "authentification"
python3 ai_smartness_v2/cli/main.py search "migration base de données"

# Limiter les résultats
python3 ai_smartness_v2/cli/main.py search "api" --limit 5
```

---

## GuardCode

GuardCode protège votre processus de développement avec des règles configurables.

### Règles par Défaut

| Règle | Effet |
|-------|-------|
| `enforce_plan_mode` | Bloque les changements de code sans plan validé |
| `warn_quick_solutions` | Rappelle que simple ≠ meilleur |
| `require_all_choices` | Doit présenter toutes les alternatives |

### Comment ça Marche

Avant chaque prompt, GuardCode vérifie:
1. Y a-t-il un plan actif pour ce travail?
2. Le plan a-t-il été validé par l'utilisateur?
3. Y a-t-il des alternatives à présenter?

Si les règles sont violées, des rappels sont injectés dans le contexte.

### Configuration

Éditez `ai_smartness_v2/.ai/config.json`:

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

## Bonnes Pratiques

### Laissez le Système Travailler

N'essayez pas d'"aider" le système - il capture tout automatiquement. Simplement:
- Travaillez normalement
- Prenez des décisions explicitement quand demandé
- Laissez les threads se former naturellement

### Reprise de Session

Quand vous démarrez une nouvelle session:
1. Le système injecte le contexte automatiquement
2. Vous pouvez vérifier le status: `python3 ai_smartness_v2/cli/main.py status`
3. Votre agent aura accès au contexte précédent

### Projets Longs

Pour les projets s'étalant sur semaines/mois:
- Les threads accumulent les connaissances
- Les bridges connectent le travail lié
- Le contexte est synthétisé à 95%
- La reprise se fait sans friction

### Grands Projets

Pour les grandes codebases (blockchain, entreprise):
- Augmentez la limite de threads dans la config
- Le mode "heavy" supporte jusqu'à 100 threads
- Éditez la config pour aller plus haut si nécessaire

---

## Configuration

### Limites de Threads

```json
{
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100
  }
}
```

| Mode | Limite par défaut | Usage typique |
|------|-------------------|---------------|
| light | 15 | Petits projets |
| normal | 50 | Projets moyens |
| heavy | 100 | Grands/complexes projets |

### Modèle d'Extraction

```json
{
  "llm": {
    "extraction_model": "claude-3-5-haiku-20241022",
    "claude_cli_path": "/usr/local/bin/claude"
  }
}
```

L'extraction utilise toujours Haiku (économique). C'est indépendant du modèle de votre agent principal.

---

## Dépannage

### "Heuristic fallback" dans les titres

Le CLI Claude n'a pas été trouvé. Vérifiez:
```bash
which claude
```

Si non trouvé, installez le CLI Claude Code ou mettez à jour le chemin dans la config.

### Les captures ne se font pas

Vérifiez les hooks dans `.claude/settings.json`:
- Les chemins doivent être **absolus**
- Python3 doit être dans le PATH

### Trop de threads

Augmentez la limite:
```json
"active_threads_limit": 150
```

### Drift de contexte

Si l'agent semble "oublier" le contexte:
1. Vérifiez le status des threads: les threads actifs ont le contexte
2. Vérifiez les bridges: les threads liés devraient être connectés
3. La synthèse à 95% préserve les infos clés

---

## Fichiers de Base de Données

Emplacement: `ai_smartness_v2/.ai/`

| Fichier/Dossier | Contenu |
|-----------------|---------|
| `config.json` | Configuration |
| `db/threads/` | Fichiers JSON Thread |
| `db/bridges/` | Fichiers JSON Bridge |
| `db/synthesis/` | Synthèses de compactage |

### Inspection Manuelle

```bash
# Compter les threads
ls ai_smartness_v2/.ai/db/threads/ | wc -l

# Compter les bridges
ls ai_smartness_v2/.ai/db/bridges/ | wc -l

# Voir un thread
cat ai_smartness_v2/.ai/db/threads/thread_20260128_143022_abc123.json | python3 -m json.tool
```

---

## Ce que v2 NE FAIT PAS

| Fonctionnalité | Pourquoi Non |
|----------------|--------------|
| Requiert une action utilisateur | 100% transparent |
| Utilise des regex pour la sémantique | LLM uniquement pour le sens |
| Hardcode des seuils | Le LLM décide intelligemment |
| Pollue vos prompts | Le contexte est invisible |
| Requiert une configuration | Fonctionne out of the box |

---

## Support

Si vous rencontrez des problèmes:
1. Vérifiez `.claude/settings.json` pour les chemins de hooks corrects
2. Vérifiez que le CLI Claude est accessible
3. Consultez les comptes thread/bridge avec le CLI
4. Vérifiez `ai_smartness_v2/.ai/` pour l'intégrité de la base
