# AI Smartness - Token Tracking (Future Feature)

## Contexte

Le problème "prompt too long" survient quand le contexte total dépasse la limite de l'API Anthropic (~200K tokens). Actuellement on limite en **caractères** (8000 chars), mais un tracking en **tokens** serait plus précis.

## Limite Actuelle

| Source | Limite | ~Tokens |
|--------|--------|---------|
| `additionalContext` (recall) | 8000 chars | ~2000-2500 |
| `inject.py` memory context | variable | variable |
| Conversation history | non contrôlé | variable |
| System prompts Claude Code | non contrôlé | variable |

**Problème**: On ne contrôle qu'une partie du contexte total.

## Objectif

Tracker les tokens injectés par AI Smartness pour:
1. Logging/debugging précis
2. Ajustement dynamique des limites
3. Éviter les "prompt too long" de manière proactive

## Approches Possibles

### 1. Estimation Simple (Recommandé v1)

```python
def estimate_tokens(text: str, lang: str = "mixed") -> int:
    """
    Estimate token count from text.

    Rule of thumb:
    - English: ~4 chars/token
    - French: ~3.5 chars/token
    - Code: ~3 chars/token
    """
    ratio = {"en": 4.0, "fr": 3.5, "code": 3.0, "mixed": 3.5}
    return int(len(text) / ratio.get(lang, 3.5))
```

**Avantages**: Zéro dépendance, rapide
**Inconvénients**: Approximation (~20% d'erreur possible)

### 2. Tokenizer Tiers (tiktoken)

```python
import tiktoken

def count_tokens_tiktoken(text: str) -> int:
    """Count tokens using OpenAI's tiktoken (cl100k_base)."""
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))
```

**Avantages**: Plus précis (~5-10% d'erreur vs Claude)
**Inconvénients**: Dépendance supplémentaire, pas exact pour Claude

### 3. API Anthropic (Futur)

Anthropic ne fournit pas de tokenizer public. Options futures:
- Endpoint `/tokenize` (n'existe pas encore)
- SDK avec méthode de comptage

## Implémentation Proposée

### Phase 1: Logging Estimé

Modifier `pretool.py` et `inject.py`:

```python
# Constants
CHARS_PER_TOKEN = 3.5  # Conservative estimate

def log_with_tokens(message: str, chars: int):
    """Log with estimated token count."""
    tokens = int(chars / CHARS_PER_TOKEN)
    log(f"{message} ({chars} chars, ~{tokens} tokens)")
```

### Phase 2: Limites Dynamiques

```python
# config.json
{
  "settings": {
    "token_limits": {
      "recall_max_tokens": 2000,
      "inject_max_tokens": 3000,
      "total_budget_tokens": 8000
    }
  }
}
```

```python
def get_token_limit(config: dict, key: str) -> int:
    """Get token limit from config."""
    limits = config.get("settings", {}).get("token_limits", {})
    defaults = {
        "recall_max_tokens": 2000,
        "inject_max_tokens": 3000,
        "total_budget_tokens": 8000
    }
    return limits.get(key, defaults.get(key, 2000))

def chars_from_tokens(tokens: int) -> int:
    """Convert token limit to char limit."""
    return int(tokens * CHARS_PER_TOKEN)
```

### Phase 3: Budget Partagé

```python
class TokenBudget:
    """Track token usage across injection points."""

    def __init__(self, total_budget: int = 8000):
        self.total_budget = total_budget
        self.used = 0

    def allocate(self, tokens: int) -> int:
        """Allocate tokens, return actual allocation."""
        available = self.total_budget - self.used
        actual = min(tokens, available)
        self.used += actual
        return actual

    def remaining(self) -> int:
        return self.total_budget - self.used
```

## Fichiers à Modifier

| Fichier | Modification |
|---------|-------------|
| `hooks/pretool.py` | Logging tokens estimés, limite configurable |
| `hooks/inject.py` | Logging tokens estimés, limite configurable |
| `config.json` | Nouvelles options `token_limits` |
| `cli/commands/status.py` | Afficher stats tokens |

## CLI

```bash
ai status
# Ajout:
# Token Budget: ~2500/8000 used (recall: 1200, inject: 1300)

ai config token_limits.recall_max_tokens 1500
# Set recall token limit to 1500
```

## Métriques

Nouveau fichier `.ai/token_stats.json`:

```json
{
  "last_injection": {
    "timestamp": "2026-01-31T10:30:00",
    "recall_tokens": 1200,
    "inject_tokens": 1300,
    "total_tokens": 2500
  },
  "daily_avg": {
    "recall": 800,
    "inject": 1000
  },
  "errors": {
    "prompt_too_long_count": 2,
    "last_error_at": "2026-01-31T09:15:00"
  }
}
```

## Contraintes

1. **Pas de tokenizer officiel Anthropic** - on reste en estimation
2. **Contexte externe non contrôlé** - conversation + system prompts de Claude Code
3. **Limite API variable** - peut changer selon le modèle/tier

## Priorité

| Phase | Effort | Impact |
|-------|--------|--------|
| 1 (Logging) | Faible | Moyen - visibilité |
| 2 (Config) | Moyen | Élevé - flexibilité |
| 3 (Budget) | Élevé | Élevé - proactif |

## Notes

- La limite de 200K tokens est pour le **contexte total** (input + output potentiel)
- Claude Code réserve probablement une partie pour sa propre utilisation
- En pratique, viser ~10-15K tokens max pour les injections AI Smartness semble safe

## Références

- [Anthropic Token Counting](https://docs.anthropic.com/en/docs/build-with-claude/token-counting) - Documentation officielle
- [tiktoken](https://github.com/openai/tiktoken) - Tokenizer OpenAI (approximation)
