# AI Smartness v4.4 - MCP Server

## Contexte

Le hook `PreToolUse` est bugué dans Claude Code VSCode (bug connu depuis novembre, non patché). Les chemins virtuels `.ai/recall/*` ne peuvent pas être interceptés.

**Solution** : Exposer les fonctionnalités via un **serveur MCP** (Model Context Protocol) local. L'agent utilise des outils natifs au lieu de Read hackés.

---

## Pourquoi MCP ?

| Critère | Read + PreToolUse | MCP Server |
|---------|-------------------|------------|
| Fonctionne | ❌ Bug VSCode | ✅ Stable |
| Élégance | Hack | Natif |
| Dépendances | - | `mcp` (pip) |
| Complexité | - | Simple |
| Local | ✅ | ✅ |

MCP est le bon niveau d'abstraction : des **outils déclarés** que l'agent peut appeler nativement.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code Agent                        │
│                                                              │
│   ai_recall("auth")   ai_merge("t1","t2")   ai_help()       │
└──────────────────────────┬───────────────────────────────────┘
                           │ stdio (JSON-RPC)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  AI Smartness MCP Server                     │
│                    (mcp/server.py)                           │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  ai_recall  │  │  ai_merge   │  │  ai_split   │  ...    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                  │
│         └────────────────┴────────────────┘                  │
│                          │                                   │
│                          ▼                                   │
│              ┌───────────────────────┐                      │
│              │   AI Smartness Core   │                      │
│              │  (recall.py, etc.)    │                      │
│              └───────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Outils MCP Exposés

### `ai_recall`

Recherche sémantique dans la mémoire.

```json
{
  "name": "ai_recall",
  "description": "Search semantic memory for relevant threads, summaries, and bridges",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query (keyword, topic, or thread_id)"
      }
    },
    "required": ["query"]
  }
}
```

**Exemples d'appel** :
- `ai_recall(query="authentication")` → threads sur l'auth
- `ai_recall(query="thread_abc123")` → thread spécifique
- `ai_recall(query="hooks configuration")` → recherche multi-mots

**Retour** : Markdown avec threads matchés, scores, résumés, bridges.

---

### `ai_merge`

Fusionne deux threads pour libérer du contexte.

```json
{
  "name": "ai_merge",
  "description": "Merge two threads. Survivor absorbs messages/topics from absorbed thread.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "survivor_id": {
        "type": "string",
        "description": "Thread ID that will absorb the other"
      },
      "absorbed_id": {
        "type": "string",
        "description": "Thread ID to be absorbed (will be archived)"
      }
    },
    "required": ["survivor_id", "absorbed_id"]
  }
}
```

**Retour** : Confirmation ou erreur (split_locked, not found, etc.)

---

### `ai_split`

Divise un thread qui a drifté en plusieurs sujets.

```json
{
  "name": "ai_split",
  "description": "Split a thread into multiple threads. Step 1: list messages. Step 2: confirm split.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "thread_id": {
        "type": "string",
        "description": "Thread ID to split"
      },
      "confirm": {
        "type": "boolean",
        "description": "False = list messages, True = execute split",
        "default": false
      },
      "titles": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Titles for new threads (required if confirm=true)"
      },
      "message_groups": {
        "type": "array",
        "items": {
          "type": "array",
          "items": {"type": "string"}
        },
        "description": "Message IDs grouped by new thread (required if confirm=true)"
      },
      "lock_mode": {
        "type": "string",
        "enum": ["compaction", "agent_release", "force"],
        "default": "compaction",
        "description": "Split lock mode for new threads"
      }
    },
    "required": ["thread_id"]
  }
}
```

**Workflow** :
1. `ai_split(thread_id="abc")` → Liste messages avec IDs
2. `ai_split(thread_id="abc", confirm=true, titles=["T1","T2"], message_groups=[["m1","m2"],["m3"]])` → Exécute

---

### `ai_unlock`

Déverrouille un thread split_locked.

```json
{
  "name": "ai_unlock",
  "description": "Remove split_lock from a thread, allowing it to be merged",
  "inputSchema": {
    "type": "object",
    "properties": {
      "thread_id": {
        "type": "string",
        "description": "Thread ID to unlock"
      }
    },
    "required": ["thread_id"]
  }
}
```

---

### `ai_help`

Documentation des capacités.

```json
{
  "name": "ai_help",
  "description": "Get AI Smartness documentation and current memory stats",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

---

### `ai_status`

Status actuel de la mémoire.

```json
{
  "name": "ai_status",
  "description": "Get current memory status: thread counts, bridges, last activity",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

---

## Implémentation

### Dépendances

```bash
pip install mcp
```

Le package `mcp` fournit le SDK Python pour créer des serveurs MCP.

### Structure des Fichiers

```
ai_smartness/
├── mcp/
│   ├── __init__.py
│   ├── server.py          ← Point d'entrée MCP
│   └── tools.py           ← Définition des outils
├── hooks/
│   └── recall.py          ← Logique existante (réutilisée)
└── ...
```

### Serveur MCP

```python
# ai_smartness/mcp/server.py

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pathlib import Path
import sys

# Add package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_smartness.mcp.tools import (
    recall_tool,
    merge_tool,
    split_tool,
    unlock_tool,
    help_tool,
    status_tool,
)

# Create server
server = Server("ai-smartness")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available AI Smartness tools."""
    return [
        recall_tool.definition,
        merge_tool.definition,
        split_tool.definition,
        unlock_tool.definition,
        help_tool.definition,
        status_tool.definition,
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute an AI Smartness tool."""

    # Get AI path from environment or detect
    ai_path = get_ai_path()

    handlers = {
        "ai_recall": recall_tool.execute,
        "ai_merge": merge_tool.execute,
        "ai_split": split_tool.execute,
        "ai_unlock": unlock_tool.execute,
        "ai_help": help_tool.execute,
        "ai_status": status_tool.execute,
    }

    if name not in handlers:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = await handlers[name](arguments, ai_path)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


def get_ai_path() -> Path:
    """Detect the .ai directory path."""
    # Try current working directory
    cwd = Path.cwd()
    if (cwd / ".ai").exists():
        # Resolve symlink if needed
        ai_path = (cwd / ".ai").resolve()
        return ai_path

    # Try package-relative
    package_root = Path(__file__).parent.parent
    if (package_root / ".ai").exists():
        return package_root / ".ai"

    raise RuntimeError("Cannot find .ai directory")


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
```

### Définition d'un Outil

```python
# ai_smartness/mcp/tools.py

from mcp.types import Tool
from pathlib import Path

class RecallTool:
    definition = Tool(
        name="ai_recall",
        description="Search semantic memory for relevant threads, summaries, and bridges",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keyword, topic, or thread_id)"
                }
            },
            "required": ["query"]
        }
    )

    @staticmethod
    async def execute(arguments: dict, ai_path: Path) -> str:
        """Execute recall search."""
        query = arguments.get("query", "")

        # Import existing recall logic
        from ai_smartness.hooks.recall import handle_recall
        return handle_recall(query, ai_path)


recall_tool = RecallTool()

# ... similar for other tools
```

---

## Configuration Claude Code

### settings.json

```json
{
  "mcpServers": {
    "ai-smartness": {
      "command": "python3",
      "args": ["/absolute/path/to/ai_smartness/mcp/server.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/project"
      }
    }
  }
}
```

### Installation automatique (install.sh)

```bash
# Dans install.sh

configure_mcp() {
    local project_path="$1"
    local package_path="$2"

    # Create or update .claude/settings.json
    local settings_file="$project_path/.claude/settings.json"

    # Add mcpServers configuration
    # ... (merge with existing config)

    echo "✅ MCP server configured"
}
```

---

## Migration depuis v4.3

### Changements pour l'agent

| Avant (v4.3) | Après (v4.4) |
|--------------|--------------|
| `Read(".ai/recall/auth")` | `ai_recall(query="auth")` |
| `Read(".ai/merge/t1/t2")` | `ai_merge(survivor_id="t1", absorbed_id="t2")` |
| `Read(".ai/split/t1")` | `ai_split(thread_id="t1")` |
| `Read(".ai/help")` | `ai_help()` |

### Rétrocompatibilité

Les hooks existants (UserPromptSubmit, PostToolUse, PreCompact) restent inchangés.
Seul le mécanisme d'accès aux commandes agent change.

### Documentation agent mise à jour

Le contexte injecté via UserPromptSubmit doit être mis à jour :

```markdown
🧠 AI SMARTNESS

Tools disponibles:
- ai_recall(query) - Recherche sémantique
- ai_merge(survivor_id, absorbed_id) - Fusionner threads
- ai_split(thread_id, ...) - Diviser thread
- ai_unlock(thread_id) - Déverrouiller
- ai_help() - Documentation
- ai_status() - Status mémoire
```

---

## Tests

### Test manuel du serveur

```bash
# Terminal 1: Lancer le serveur en mode debug
cd /path/to/project
python3 -m ai_smartness.mcp.server

# Terminal 2: Envoyer une requête JSON-RPC
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 -m ai_smartness.mcp.server
```

### Test avec Claude Code

```bash
# Lancer Claude avec debug
claude --debug

# Vérifier que le MCP server est chargé
# Les outils ai_* devraient apparaître dans les tools disponibles
```

---

## Avantages de cette approche

1. **Pas de hack** - Utilise l'infrastructure MCP officielle
2. **100% local** - Process Python, communication stdio
3. **Réutilise le code existant** - recall.py, etc.
4. **Déclaratif** - Les outils sont documentés via leur schema
5. **Extensible** - Facile d'ajouter de nouveaux outils
6. **Stable** - MCP est une spec stable, pas un hack de hook

---

## Checklist d'implémentation

- [ ] Créer `ai_smartness/mcp/__init__.py`
- [ ] Créer `ai_smartness/mcp/server.py` (serveur principal)
- [ ] Créer `ai_smartness/mcp/tools.py` (définitions outils)
- [ ] Adapter `recall.py` pour être appelable depuis MCP
- [ ] Modifier `install.sh` pour configurer MCP
- [ ] Mettre à jour `inject.py` (documentation agent)
- [ ] Ajouter `mcp` aux dépendances
- [ ] Tests unitaires
- [ ] Tests intégration avec Claude Code

---

## Effort estimé

| Tâche | Temps |
|-------|-------|
| Structure MCP + server.py | 1h |
| Tools definitions | 1h |
| Adaptation recall.py | 30min |
| Install.sh + config | 30min |
| Mise à jour inject.py | 30min |
| Tests | 1h |
| **Total** | **~5h** |

Beaucoup plus simple que FUSE (12h), et plus propre !

---

*AI Smartness v4.4 - MCP Server Specification*
*Date: 2026-01-31*
