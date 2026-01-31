# Plan d'implémentation - AI Smartness v2

## Contexte

**Spec**: [SPEC_V2.md](src/ai_smartness-v2/SPEC_V2.md)
**Objectif**: Couche de méta-cognition pour agents LLM avec mémoire persistante

### Contraintes
- 100% LLM pour le raisonnement sémantique
- Zéro action utilisateur requise
- Transparent et invisible
- **Forfait MAX Anthropic** : pas de coûts API externes pour embeddings
- **Chemins absolus obligatoires** : éviter le problème v1 des chemins relatifs
- **Anti-autohook** : empêcher les boucles de hooks

### Décisions techniques
- **LLM extraction** : Haiku par défaut (économique), configurable
- **Embeddings** : sentence-transformers local (gratuit, offline)
- **Approche** : Phase par phase

## Architecture cible

```
src/ai_smartness-v2/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── thread.py          # Modèle Thread
│   └── bridge.py          # Modèle ThinkBridge
├── storage/
│   ├── __init__.py
│   ├── manager.py         # StorageManager principal
│   ├── threads.py         # ThreadStorage
│   └── bridges.py         # BridgeStorage
├── processing/
│   ├── __init__.py
│   ├── extractor.py       # Extraction LLM
│   ├── embeddings.py      # Gestion embeddings
│   └── classifier.py      # Classification par LLM
├── intelligence/
│   ├── __init__.py
│   ├── thread_manager.py  # Cycle de vie threads
│   ├── gossip.py          # Propagation ThinkBridges
│   └── synthesis.py       # Synthèse à 95%
├── guardcode/
│   ├── __init__.py
│   ├── enforcer.py        # Règles GuardCode
│   └── injector.py        # Micro-injection contexte
├── hooks/
│   ├── __init__.py
│   ├── capture.py         # Hook capture (post-tool)
│   ├── inject.py          # Hook injection (pre-prompt)
│   └── compact.py         # Hook compactage (95%)
└── config.py              # Configuration
```

---

## Phase 1: Core Foundation

### 1.1 Modèles de données

**Fichier**: `models/thread.py`
```python
@dataclass
class Thread:
    id: str
    title: str
    status: Literal["active", "suspended", "archived"]
    messages: List[Message]
    summary: str
    origin_type: str
    drift_history: List[str]
    parent_id: Optional[str]
    child_ids: List[str]
    weight: float
    last_active: datetime
    embedding: Optional[List[float]]
```

**Fichier**: `models/bridge.py`
```python
@dataclass
class ThinkBridge:
    id: str
    source_id: str
    target_id: str
    relation_type: str
    reason: str
    confidence: float
    propagation_depth: int
```

### 1.2 Storage basique

**Fichier**: `storage/manager.py`
- Initialisation DB structure
- Load/save JSON

**Fichier**: `storage/threads.py`
- CRUD threads
- Index par status

**Fichier**: `storage/bridges.py`
- CRUD bridges
- Index source/target

### 1.3 Hook capture basique

**Fichier**: `hooks/capture.py`
- Réception des tool results
- Pré-filtre heuristique (tags IDE, JSON noise)
- Passage au processing

### Vérification Phase 1
- [ ] Créer un thread manuellement via code
- [ ] Sauvegarder/charger depuis JSON
- [ ] Hook capture reçoit les events

---

## Phase 2: Intelligence

### 2.1 Extraction LLM

**Fichier**: `processing/extractor.py`
```python
class LLMExtractor:
    def extract(self, content: str, source_type: str) -> Extraction:
        """
        Appelle LLM pour extraire:
        - intent
        - subjects/topics
        - questions
        - implicit_context
        """
```

**Prompts par source**:
- `prompt`: Intention utilisateur, questions posées
- `read`: But de la lecture, concepts clés
- `write`: Ce qui a changé, pourquoi
- `task`: Résultat final, décisions

### 2.2 Embeddings

**Fichier**: `processing/embeddings.py`
```python
class EmbeddingManager:
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        # Local par défaut, option API

    def embed(self, text: str) -> List[float]
    def similarity(self, a: List[float], b: List[float]) -> float
```

### 2.3 Thread lifecycle

**Fichier**: `intelligence/thread_manager.py`
```python
class ThreadManager:
    def process_input(self, content: str, source: str) -> Thread:
        """
        1. Extraction LLM
        2. Décision: nouveau thread / continuation / fork / réactivation
        3. Mise à jour poids et embedding
        """

    def decide_action(self, extraction: Extraction) -> ThreadAction:
        """
        LLM décide (pas de seuils hardcodés):
        - NEW_THREAD
        - CONTINUE
        - FORK
        - REACTIVATE
        """
```

### 2.4 ThinkBridges & Gossip

**Fichier**: `intelligence/gossip.py`
```python
class GossipPropagator:
    def propagate(self, modified_thread: Thread):
        """
        1. Calcul nouvel embedding
        2. Pour chaque thread connecté
        3. Si similarité suffisante → propager bridges
        """

    def should_create_bridge(self, a: Thread, b: Thread) -> Optional[BridgeType]:
        """LLM décide du type de relation"""
```

### Vérification Phase 2
- [ ] Extraction retourne des données structurées
- [ ] Embeddings calculés correctement
- [ ] Threads créés/continués selon contexte
- [ ] Bridges créés entre threads liés

---

## Phase 3: GuardCode & Injection

### 3.1 Micro-injection

**Fichier**: `guardcode/injector.py`
```python
class ContextInjector:
    def build_injection(self) -> str:
        """
        Construit le contexte invisible:
        - Thread actif
        - Décisions en cours
        - Contraintes projet
        """
        return f"<!-- ai_smartness: {context_json} -->"
```

### 3.2 Enforcement

**Fichier**: `guardcode/enforcer.py`
```python
class GuardCodeEnforcer:
    rules = [
        PlanModeRequired(),
        NoQuickSolutions(),
        PresentAllChoices(),
    ]

    def check(self, user_prompt: str) -> List[Reminder]:
        """Retourne les rappels à injecter"""
```

### 3.3 Hook injection

**Fichier**: `hooks/inject.py`
- UserPromptSubmit hook
- Injecte contexte + GuardCode
- 100% invisible

### 3.4 Synthèse à 95%

**Fichier**: `intelligence/synthesis.py`
```python
class ContextSynthesizer:
    def synthesize(self) -> str:
        """
        Génère synthèse LLM:
        - Décisions prises
        - Questions ouvertes
        - État du travail
        """
```

**Fichier**: `hooks/compact.py`
- Détection 95% context
- Trigger synthèse
- Sauvegarde état

### Vérification Phase 3
- [ ] Injection invisible dans les prompts
- [ ] GuardCode rappelle le plan mode
- [ ] Synthèse générée à 95%

---

## Phase 4: Intégration & Polish

### 4.1 Configuration

**Fichier**: `config.py`
```python
@dataclass
class Config:
    project_name: str
    language: str
    llm_model: str
    embedding_model: str
    auto_capture: bool
```

### 4.2 CLI (optionnel)

**Fichier**: `cli.py`
- `ai status` - État actuel
- `ai threads` - Liste threads
- `ai search` - Recherche

### 4.3 Migration v1 (optionnel)

- Script d'import des threads v1
- Recalcul embeddings
- Nettoyage pollution

### Vérification Phase 4
- [ ] Config chargée au démarrage
- [ ] CLI fonctionnel
- [ ] Session longue sans drift

---

## Fichiers critiques à créer

| Fichier | Action | Priorité |
|---------|--------|----------|
| `src/ai_smartness-v2/models/thread.py` | CREATE | Phase 1 |
| `src/ai_smartness-v2/models/bridge.py` | CREATE | Phase 1 |
| `src/ai_smartness-v2/storage/manager.py` | CREATE | Phase 1 |
| `src/ai_smartness-v2/storage/threads.py` | CREATE | Phase 1 |
| `src/ai_smartness-v2/processing/extractor.py` | CREATE | Phase 2 |
| `src/ai_smartness-v2/processing/embeddings.py` | CREATE | Phase 2 |
| `src/ai_smartness-v2/intelligence/thread_manager.py` | CREATE | Phase 2 |
| `src/ai_smartness-v2/intelligence/gossip.py` | CREATE | Phase 2 |
| `src/ai_smartness-v2/guardcode/enforcer.py` | CREATE | Phase 3 |
| `src/ai_smartness-v2/guardcode/injector.py` | CREATE | Phase 3 |
| `src/ai_smartness-v2/hooks/capture.py` | CREATE | Phase 1 |
| `src/ai_smartness-v2/hooks/inject.py` | CREATE | Phase 3 |
| `src/ai_smartness-v2/install.sh` | CREATE | Phase 4 |

---

## Corrections des problèmes v1

### Problème 1: Chemins relatifs

**v1 (cassé):**
```bash
command: "python3 ai_smartness/hooks/capture.py"  # Relatif = fail
```

**v2 (fix):**
```bash
# À l'installation, résoudre le chemin absolu
AI_PATH="$(cd "$TARGET_DIR/ai_smartness-v2" && pwd)"
command: "python3 $AI_PATH/hooks/capture.py"  # Absolu = OK
```

### Problème 2: Boucle autohook

**v1 (cassé):**
```
UserPromptSubmit → capture.py → traitement → génère output
                                              ↓
PostToolUse → capture.py → traitement → génère output → ...
```

**v2 (fix):**
```python
# Au début de chaque hook
import os
if os.environ.get('AI_SMARTNESS_HOOK_RUNNING'):
    sys.exit(0)  # Déjà dans un hook, ne pas re-déclencher

os.environ['AI_SMARTNESS_HOOK_RUNNING'] = '1'
try:
    # ... traitement
finally:
    del os.environ['AI_SMARTNESS_HOOK_RUNNING']
```

### Problème 3: install.sh adapté

Conserver de v1:
- Sélection langue (en/fr/es)
- Sélection mode (heavy/normal/light)
- Option garder/reset DB
- Configuration .gitignore et .claudeignore

Modifier pour v2:
- Chemins absolus dans settings.json
- Nouvelle structure de DB (threads seulement, pas fragments)
- Hooks v2 (capture, inject, compact)

---

## Décisions prises

| Question | Décision |
|----------|----------|
| LLM extraction | Haiku par défaut (configurable) |
| Embeddings | sentence-transformers local (forfait MAX) |
| Approche | Phase par phase |
| Chemins | Absolus, résolus à l'install |
| Anti-autohook | Env var guard |

---

## Vérification end-to-end

### Phase 1 - Core
```bash
# Test création thread
python3 -c "
from models.thread import Thread
t = Thread.create('test', 'Test thread')
print(f'Thread created: {t.id}')
"

# Test persistence
ls -la .ai/db/threads/
```

### Phase 2 - Intelligence
```bash
# Test extraction LLM
python3 -c "
from processing.extractor import LLMExtractor
e = LLMExtractor()
result = e.extract('Comment fonctionne l\\'API?', 'prompt')
print(result)
"

# Test embeddings
python3 -c "
from processing.embeddings import EmbeddingManager
em = EmbeddingManager()
v1 = em.embed('API authentication')
v2 = em.embed('Auth endpoints')
print(f'Similarity: {em.similarity(v1, v2):.3f}')
"
```

### Phase 3 - GuardCode
```bash
# Test injection
python3 hooks/inject.py --message "test prompt" | head -5
# Doit montrer le contexte injecté (invisible pour user)
```

### Phase 4 - Intégration
```bash
# Test install complet
cd /tmp && mkdir test_project && cd test_project
/path/to/ai_smartness-v2/install.sh .
# Vérifier: .claude/settings.json avec chemins absolus
```

---

## Estimation

| Phase | Fichiers | Complexité |
|-------|----------|------------|
| Phase 1 | 6 | Moyenne |
| Phase 2 | 5 | Haute |
| Phase 3 | 4 | Moyenne |
| Phase 4 | 3 | Basse |

**Total**: ~18 fichiers Python + install.sh + i18n

---

## État actuel

**Phases 1-4: COMPLÉTÉES**
- Tous les fichiers créés et testés
- Tests d'intégration passent

**Problème identifié:**
Le hook `capture.py` log les captures mais NE CRÉE PAS les threads.
La fonction `process_capture()` est un stub qui n'intègre pas avec ThreadManager.

---

## Phase 5: Finalisation capture.py

### Objectif
Compléter l'intégration de `capture.py` pour qu'il crée réellement des threads.

### Fichier à modifier
`src/ai_smartness/hooks/capture.py`

### Architecture choisie: Daemon avec Socket Unix

**Décision**: Daemon permanent avec communication via socket Unix

**Avantages**:
- Chargement des modules une seule fois
- Très rapide (pas d'init Python à chaque call)
- Isolation complète du hook
- Peut battre les captures (traiter en batch)

**Composants**:

1. **`daemon/processor.py`** - Le daemon principal
   ```python
   class ProcessorDaemon:
       def __init__(self, db_path: Path):
           # Charge une seule fois
           self.storage = StorageManager(db_path)
           self.thread_manager = ThreadManager(self.storage)
           self.gossip = GossipPropagator(self.storage)
           self.socket_path = db_path.parent / "processor.sock"

       def run(self):
           # Écoute sur socket Unix
           # Traite les requêtes
           pass

       def process_capture(self, data: dict):
           # Appelle ThreadManager, GossipPropagator
           pass
   ```

2. **`daemon/client.py`** - Client léger pour les hooks
   ```python
   def send_capture(socket_path: Path, data: dict) -> bool:
       # Envoie via socket Unix
       # Retourne immédiatement (non-bloquant)
       pass
   ```

3. **`hooks/capture.py`** - Hook simplifié
   ```python
   def process_capture(tool_name, output, file_path):
       # Juste envoie au daemon via client
       from ..daemon.client import send_capture
       send_capture(socket_path, {
           "tool": tool_name,
           "content": output,
           "file_path": file_path
       })
   ```

**Lifecycle du daemon**:
- Démarré automatiquement par `capture.py` si pas running
- PID stocké dans `.ai/processor.pid`
- Stop propre via signal ou commande

### Fichiers à créer/modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `daemon/__init__.py` | CREATE | Package daemon |
| `daemon/processor.py` | CREATE | Daemon principal avec socket |
| `daemon/client.py` | CREATE | Client léger pour hooks |
| `hooks/capture.py` | MODIFY | Utiliser client daemon |

### Détails d'implémentation

**1. `daemon/processor.py`**
```python
class ProcessorDaemon:
    def __init__(self, db_path: Path):
        self.storage = StorageManager(db_path)
        self.thread_manager = ThreadManager(self.storage)
        self.gossip = GossipPropagator(self.storage)
        self.socket_path = db_path.parent / "processor.sock"
        self.pid_file = db_path.parent / "processor.pid"

    def start(self):
        # Crée socket Unix
        # Fork en background
        # Écoute les connexions

    def handle_request(self, data: dict):
        tool = data.get("tool")
        content = data.get("content")
        file_path = data.get("file_path")

        # Map tool → source_type
        source_map = {
            "Read": "file_read",
            "Write": "file_write",
            "Task": "task",
            "WebFetch": "fetch"
        }
        source_type = source_map.get(tool, "prompt")

        # Process via ThreadManager
        thread, extraction = self.thread_manager.process_input(
            content, source_type, file_path
        )

        # Trigger gossip
        self.gossip.on_thread_modified(thread)

        return {"thread_id": thread.id, "status": "ok"}
```

**2. `daemon/client.py`**
```python
def send_capture(socket_path: Path, data: dict, timeout: float = 0.5) -> bool:
    """Envoie une capture au daemon (non-bloquant)."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(str(socket_path))
        sock.sendall(json.dumps(data).encode() + b'\n')
        sock.close()
        return True
    except:
        return False

def ensure_daemon_running(ai_path: Path) -> bool:
    """Démarre le daemon si pas déjà running."""
    pid_file = ai_path / "processor.pid"
    socket_path = ai_path / "processor.sock"

    if socket_path.exists():
        # Tester si le daemon répond
        if send_capture(socket_path, {"ping": True}):
            return True

    # Démarrer le daemon
    subprocess.Popen([
        "python3", "-m", "ai_smartness.daemon.processor",
        "--db-path", str(ai_path / "db")
    ], start_new_session=True)

    return True
```

**3. `hooks/capture.py` (modifié)**
```python
def process_capture(tool_name, output, file_path):
    cleaned, should_process = filter_noise(output)
    if not should_process:
        return

    # Trouver le chemin .ai
    ai_path = get_ai_path()

    # S'assurer que le daemon tourne
    ensure_daemon_running(ai_path)

    # Envoyer au daemon
    send_capture(ai_path / "processor.sock", {
        "tool": tool_name,
        "content": cleaned,
        "file_path": file_path
    })
```

### Vérification
- [ ] Daemon démarre automatiquement au premier capture
- [ ] Socket `.ai/processor.sock` créé
- [ ] Après un Read, thread créé dans `.ai/db/threads/`
- [ ] Bridges créés si similarité suffisante
- [ ] Hook capture retourne rapidement (< 100ms)

---

## Phase 5: COMPLÉTÉE ✓

- Daemon créé et fonctionnel
- 31 threads et 384 bridges créés sur KratOs
- Hook capture intégré avec ThreadManager

---

## Phase 6: Améliorations Extraction & CLI

### Objectifs
1. **Extraction LLM pour meilleurs titres** - Remplacer "Extraction heuristique (LLM non disponible)"
2. **Nettoyage des topics** - Retirer "MESSAGE:", "Analyse", et autres bruits
3. **CLI pour visualiser** - Interface console pour threads/bridges

---

### 6.1 Amélioration de l'extraction LLM

**Problème actuel:**
- `extractor.py` utilise `claude` CLI subprocess avec juste `"claude"`
- Le daemon tourne en background sans PATH complet → CLI introuvable
- Fallback heuristique avec titres "Extraction heuristique (LLM non disponible)"

**Contrainte importante:**
- Forfait MAX = CLI illimité gratuit
- API = crédits supplémentaires (à éviter)
- Donc: utiliser le CLI `claude` avec chemin absolu

**Solution: Chemin absolu du CLI + config modèle**

1. **`install.sh`** détecte le chemin du CLI:
```bash
# Détecter le chemin de claude
CLAUDE_PATH=$(which claude 2>/dev/null)
if [ -z "$CLAUDE_PATH" ]; then
    echo "ERREUR: CLI 'claude' non trouvé. Installer Claude Code d'abord."
    exit 1
fi

# Sauvegarder dans config.json
# + le modèle choisi (haiku/sonnet/opus)
```

2. **`config.json`** stocke le chemin:
```json
{
  "llm": {
    "extraction_model": "claude-haiku-3-5-20250620",
    "claude_cli_path": "/home/user/.local/bin/claude"
  }
}
```

3. **`extractor.py`** lit la config:
```python
def _call_llm(self, prompt: str) -> str:
    """Appelle LLM via CLI Claude avec chemin absolu."""
    try:
        result = subprocess.run(
            [self.claude_cli_path, "--model", self.model, "--print", prompt],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logger.warning(f"CLI failed: {result.stderr}")
            return self._fallback_extraction(prompt)
    except FileNotFoundError:
        logger.error(f"CLI not found at {self.claude_cli_path}")
        return self._fallback_extraction(prompt)
```

**Fichiers à modifier:**

| Fichier | Modification |
|---------|--------------|
| `install.sh` | Détecter `which claude`, sauver dans config, extraction_model selon mode |
| `processing/extractor.py` | Lire config, utiliser `claude_cli_path` absolu |
| `intelligence/thread_manager.py` | Passer config à LLMExtractor |

**Gestion des modèles selon performance:**

| Mode install.sh | Modèle extraction |
|-----------------|-------------------|
| light | claude-haiku-3-5-20250620 |
| normal | claude-sonnet-4-20250514 |
| heavy | claude-opus-4-5-20250514 |

---

### Changements détaillés

#### 1. `install.sh` - Lignes à ajouter (après ligne 233)

```bash
# ============================================================================
# DETECT CLAUDE CLI
# ============================================================================

echo "🔍 Detecting Claude CLI..."
CLAUDE_CLI_PATH=$(which claude 2>/dev/null)

if [ -z "$CLAUDE_CLI_PATH" ]; then
    echo "   ⚠️  Claude CLI not found in PATH"
    echo "   LLM extraction will use heuristic fallback"
    CLAUDE_CLI_PATH=""
else
    echo "   ✓ Found: $CLAUDE_CLI_PATH"
fi
```

#### 2. `install.sh` - Modifier config Python (lignes 281-325)

```python
# Dans le bloc Python de config:
EXTRACTION_MODELS = {
    "light": "claude-haiku-3-5-20250620",
    "normal": "claude-sonnet-4-20250514",
    "heavy": "claude-opus-4-5-20250514"
}
extraction_model = EXTRACTION_MODELS.get(thread_mode, EXTRACTION_MODELS["normal"])

config = {
    # ... existing fields ...
    "llm": {
        "extraction_model": extraction_model,  # Changé: selon mode
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "guardian_model": guardian_model,
        "claude_cli_path": "$CLAUDE_CLI_PATH"  # NOUVEAU
    },
    # ...
}
```

#### 3. `processing/extractor.py` - Modifier `__init__` et `_call_llm`

```python
class LLMExtractor:
    def __init__(
        self,
        model: str = "claude-haiku-3-5-20250620",
        claude_cli_path: Optional[str] = None
    ):
        self.model = model
        self.claude_cli_path = claude_cli_path or "claude"  # Fallback si pas fourni

    def _call_llm(self, prompt: str) -> str:
        """Call Claude LLM with prompt using absolute path."""
        try:
            result = subprocess.run(
                [self.claude_cli_path, "--model", self.model, "--print", prompt],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return self._fallback_extraction(prompt)
        except FileNotFoundError:
            logger.warning(f"Claude CLI not found at: {self.claude_cli_path}")
            return self._fallback_extraction(prompt)
        # ... rest unchanged
```

#### 4. `intelligence/thread_manager.py` - Passer config

```python
class ThreadManager:
    def __init__(self, storage: StorageManager, extractor: Optional[LLMExtractor] = None):
        self.storage = storage

        # Si pas d'extractor fourni, le créer avec config
        if extractor is None:
            config = self._load_llm_config()
            self.extractor = LLMExtractor(
                model=config.get("extraction_model", "claude-haiku-3-5-20250620"),
                claude_cli_path=config.get("claude_cli_path")
            )
        else:
            self.extractor = extractor

    def _load_llm_config(self) -> dict:
        """Load LLM config from .ai/config.json."""
        try:
            config_path = self.storage.ai_path / "config.json"
            if config_path.exists():
                import json
                config = json.loads(config_path.read_text())
                return config.get("llm", {})
        except Exception:
            pass
        return {}

---

### 6.2 Nettoyage des topics

**Problème actuel:**
Les topics contiennent du bruit provenant des prompts LLM:
- "MESSAGE:" (préfixe du prompt)
- "Analyse" (mot générique)
- "CONTENU:" (préfixe du prompt)
- Mots trop courts ou génériques

**Solution: Filtrage post-extraction**

```python
# processing/extractor.py - Nouveau _clean_topics()

TOPIC_NOISE = {
    "message", "contenu", "analyse", "fichier", "code",
    "json", "response", "result", "data", "type", "value",
    "function", "class", "method", "variable", "parameter"
}

TOPIC_PREFIXES_TO_STRIP = ["MESSAGE:", "CONTENU:", "FICHIER:"]

def _clean_topics(self, topics: List[str]) -> List[str]:
    """Nettoie les topics en retirant le bruit."""
    cleaned = []
    for topic in topics:
        # Retirer les préfixes
        for prefix in TOPIC_PREFIXES_TO_STRIP:
            if topic.upper().startswith(prefix):
                topic = topic[len(prefix):].strip()

        # Normaliser
        topic = topic.strip().lower()

        # Filtrer le bruit
        if topic in TOPIC_NOISE:
            continue
        if len(topic) < 3:
            continue
        if not any(c.isalpha() for c in topic):
            continue

        cleaned.append(topic)

    return list(set(cleaned))  # Dédupliquer
```

**Points d'intégration:**
- Appeler `_clean_topics()` dans `_parse_response()` après extraction JSON
- Appliquer aux champs `subjects` et `key_concepts`

**Fichiers à modifier:**
- `processing/extractor.py` - Ajouter `_clean_topics()` et l'intégrer

---

### 6.3 CLI de visualisation

**Objectif:** Interface console simple pour voir l'état de la mémoire

**Commandes prévues:**

```bash
# Statut général
ai status
# Affiche: threads actifs, bridges, dernière activité

# Liste des threads
ai threads [--status active|suspended|archived] [--limit N]
# Affiche: ID, titre, status, weight, topics, message_count

# Détail d'un thread
ai thread <id>
# Affiche: titre, messages, bridges connectés, historique drift

# Liste des bridges
ai bridges [--thread <id>] [--type extends|depends|...]
# Affiche: source → target, type, confidence, reason

# Recherche sémantique
ai search "query"
# Affiche: threads triés par similarité

# Graphe (export)
ai graph [--format dot|json]
# Exporte le graphe threads+bridges
```

**Architecture CLI:**

```
src/ai_smartness/
└── cli/
    ├── __init__.py
    ├── main.py          # Entry point, argparse
    ├── commands/
    │   ├── __init__.py
    │   ├── status.py    # ai status
    │   ├── threads.py   # ai threads, ai thread
    │   ├── bridges.py   # ai bridges
    │   ├── search.py    # ai search
    │   └── graph.py     # ai graph
    └── formatters.py    # Affichage console (tables, couleurs)
```

**Fichiers à créer:**

| Fichier | Description |
|---------|-------------|
| `cli/__init__.py` | Package |
| `cli/main.py` | Parser argparse, dispatch commandes |
| `cli/commands/status.py` | Commande status |
| `cli/commands/threads.py` | Commandes threads/thread |
| `cli/commands/bridges.py` | Commande bridges |
| `cli/commands/search.py` | Recherche sémantique |
| `cli/formatters.py` | Formatage console (rich ou simple) |

**Exemple d'output:**

```
$ ai status
╭──────────────────────────────────────────╮
│ AI Smartness v2 - Memory Status          │
├──────────────────────────────────────────┤
│ Threads:  31 active, 0 suspended         │
│ Bridges:  384 connections                │
│ Last:     2026-01-28 17:40:21            │
│ Current:  "P2P Handshake Protocol"       │
╰──────────────────────────────────────────╯

$ ai threads --limit 5
 ID       │ Title                          │ Status │ Weight │ Messages
──────────┼────────────────────────────────┼────────┼────────┼──────────
 abc123.. │ P2P Handshake Protocol         │ active │  0.92  │    12
 def456.. │ Reputation System Design       │ active │  0.78  │     8
 ghi789.. │ Treasury Smart Contract        │ active │  0.65  │     5
 ...
```

**Entry point (setup.py ou pyproject.toml):**
```python
[project.scripts]
ai = "ai_smartness.cli.main:main"
```

---

### Ordre d'implémentation

1. **6.1 Extraction LLM** (priorité haute)
   - `install.sh`: Ajouter détection `which claude` + config extraction_model par mode
   - `processing/extractor.py`: Accepter `claude_cli_path` en paramètre
   - `intelligence/thread_manager.py`: Charger config LLM et passer à LLMExtractor
   - Tester sur projet existant

2. **6.2 Nettoyage topics** (priorité moyenne)
   - Ajouter `_clean_topics()` dans `extractor.py`
   - Intégrer dans `_parse_response()`

3. **6.3 CLI** (priorité basse)
   - Créer structure `cli/`
   - Implémenter commandes une par une
   - Ajouter entry point

---

### Vérification Phase 6

```bash
# 6.1 - Vérifier config après install
cat /path/to/project/ai_smartness/.ai/config.json | grep claude_cli_path
# Doit afficher le chemin absolu: "/home/user/.local/bin/claude"

# 6.1 - Test extraction avec chemin absolu
cd /path/to/project
python3 -c "
import sys
sys.path.insert(0, 'ai_smartness')
from processing.extractor import LLMExtractor

# Simuler chargement config
e = LLMExtractor(
    model='claude-haiku-3-5-20250620',
    claude_cli_path='/home/user/.local/bin/claude'  # Chemin réel
)
result = e.extract('Comment fonctionne l\\'API?', 'prompt')
print(f'Intent: {result.intent}')
# Doit afficher un vrai titre, pas 'Extraction heuristique...'
"

# 6.2 - Topics propres
python3 -c "
from ai_smartness.processing.extractor import LLMExtractor
e = LLMExtractor()
result = e.extract('MESSAGE: Analyse du fichier config', 'prompt')
print(f'Subjects: {result.subjects}')
# Ne doit PAS contenir 'MESSAGE', 'Analyse'
"

# 6.3 - CLI
ai status
ai threads --limit 3
ai bridges --thread abc123
ai search "authentication"
```

---

### Estimation Phase 6

| Tâche | Fichiers | Complexité |
|-------|----------|------------|
| 6.1 Extraction LLM | 1 modif | Moyenne |
| 6.2 Nettoyage topics | 1 modif | Basse |
| 6.3 CLI | 7 nouveaux | Moyenne |

**Total Phase 6:** ~8 fichiers

---

## Phase 7: Fix Thread Continuation

### Problème identifié

**Symptôme:** Sur KratOs, 148 threads ont tous exactement 1 message. Aucune continuation ne se produit.

**Analyse de la DB KratOs:**
- 100 active, 46 suspended threads
- 2487 bridges (dont 51% avec confiance < 0.5)
- Duplications: 4× "Configuration Nœud KratOs", 3× "GRANDPA Consensus Worker", etc.
- Tous les threads ont weight=0.66 (statique)

### Causes racines

| Composant | Bug | Fichier:Ligne | Impact |
|-----------|-----|---------------|--------|
| `get_current()` | Retourne le thread le plus récent, pas le plus pertinent | threads.py:171 | Mauvais thread sélectionné |
| Seuils trop hauts | 0.6 pour current, 0.7 pour suspended | thread_manager.py:164,176 | Threads liés rejetés |
| `_calculate_topic_similarity()` | Retourne 0 si subjects vide | thread_manager.py:213-214 | Pas de fallback sur contenu |
| `_decide_action()` | Ne vérifie que current, pas tous les actifs | thread_manager.py:149-182 | Rate les autres threads |
| `find_related_threads()` | Existe mais jamais appelé | thread_manager.py:378-409 | Mécanisme inutilisé |
| Ordre d'opérations | Embedding ajouté APRÈS décision | thread_manager.py:136 | Premier message = nouveau thread |

### Flux actuel (cassé)

```
1. Nouveau contenu arrive
   ↓
2. _decide_action() appelé AVANT embedding calculé
   ↓
3. Thread current a topics/embedding vides ou partiels
   ↓
4. _calculate_topic_similarity() retourne 0.0 ou < 0.6
   ↓
5. Tombe dans NEW_THREAD par défaut
   ↓
6. Nouveau thread créé au lieu de continuer
   ↓
7. Embedding calculé et stocké APRÈS décision
   ↓
8. Message #2 arrive → même problème → encore un nouveau thread
```

### Solution proposée

#### 7.1 Modifier `_decide_action()`

**Fichier:** `intelligence/thread_manager.py`

```python
def _decide_action(self, extraction: Extraction, content: str) -> ThreadDecision:
    """
    Decide action using comprehensive thread search.

    Priority:
    1. High similarity with ANY active thread → CONTINUE
    2. High similarity with suspended thread → REACTIVATE
    3. Otherwise → NEW_THREAD
    """
    # 1. Chercher dans TOUS les threads actifs (pas juste current)
    active_threads = self.storage.threads.get_active()

    if not active_threads:
        return ThreadDecision(NEW_THREAD, None, "No active threads", 1.0)

    # 2. Calculer similarité avec content (pas juste extraction topics)
    best_match = None
    best_similarity = 0.0

    for thread in active_threads:
        similarity = self._calculate_similarity(content, extraction, thread)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = thread

    # 3. Seuil plus bas: 0.4 au lieu de 0.6
    if best_similarity > 0.4 and best_match:
        return ThreadDecision(
            CONTINUE,
            best_match.id,
            f"Topic match {best_similarity:.2f}",
            best_similarity
        )

    # 4. Vérifier suspended avec seuil 0.5
    suspended = self.storage.threads.get_suspended()
    for thread in suspended:
        similarity = self._calculate_similarity(content, extraction, thread)
        if similarity > 0.5:
            return ThreadDecision(
                REACTIVATE,
                thread.id,
                f"Reactivate suspended {similarity:.2f}",
                similarity
            )

    # 5. Nouveau thread seulement si aucun match
    return ThreadDecision(NEW_THREAD, None, "New topic", 0.8)
```

#### 7.2 Améliorer `_calculate_similarity()`

```python
def _calculate_similarity(
    self,
    content: str,
    extraction: Extraction,
    thread: Thread
) -> float:
    """
    Calculate comprehensive similarity using multiple signals.
    """
    # Signal 1: Embedding du contenu vs embedding du thread
    content_embedding = self.embeddings.embed(content[:500])
    thread_embedding = thread.embedding

    if thread_embedding is None:
        # Fallback: embed title + topics
        thread_text = thread.title + ' ' + ' '.join(thread.topics)
        thread_embedding = self.embeddings.embed(thread_text)

    embedding_sim = self.embeddings.similarity(content_embedding, thread_embedding)

    # Signal 2: Extraction topics vs thread topics
    if extraction.subjects and thread.topics:
        common = set(s.lower() for s in extraction.subjects) & set(t.lower() for t in thread.topics)
        topic_sim = len(common) / max(len(extraction.subjects), 1)
    else:
        topic_sim = 0.0

    # Combiner: 70% embedding, 30% topics
    return 0.7 * embedding_sim + 0.3 * topic_sim
```

#### 7.3 Calculer embedding AVANT décision

**Dans `process_input()`:**

```python
def process_input(self, content: str, source_type: str, file_path: str = None):
    # 1. Extraction LLM
    extraction = self.extractor.extract(content, source_type)

    # 2. NOUVEAU: Pré-calculer embedding du contenu AVANT décision
    content_embedding = self.embeddings.embed(content[:500])

    # 3. Décision avec embedding disponible
    decision = self._decide_action(extraction, content, content_embedding)

    # 4. Suite du traitement...
```

### Fichiers à modifier

| Fichier | Changement | Priorité |
|---------|------------|----------|
| `intelligence/thread_manager.py` | Refactorer `_decide_action()` | Haute |
| `intelligence/thread_manager.py` | Améliorer `_calculate_similarity()` | Haute |
| `intelligence/thread_manager.py` | Ordre embedding dans `process_input()` | Haute |
| `storage/threads.py` | Ajouter `get_by_topic_match()` (optionnel) | Basse |

### Vérification Phase 7

```bash
# Avant fix: vérifier état actuel
cd ~/Dev/KratOs && ai threads --limit 5
# Tous ont 1 message

# Après fix + redémarrage daemon:
# Faire plusieurs lectures de fichiers liés

# Vérifier consolidation
ai threads --limit 5
# Devrait montrer messages > 1 pour threads actifs

# Vérifier pas de nouveaux duplicats
ai threads --status all | grep "Configuration" | wc -l
# Ne devrait pas augmenter
```

### Estimation Phase 7

| Tâche | Complexité |
|-------|------------|
| Refactorer `_decide_action()` | Moyenne |
| Améliorer `_calculate_similarity()` | Moyenne |
| Réordonner `process_input()` | Basse |
| Tests | Moyenne |

**Total Phase 7:** 1 fichier modifié (thread_manager.py)

---

## Phase 8: Optimisations Post-Fix

### Contexte

Après le fix du bug hash randomization (Phase 7), la continuation fonctionne mais peut être améliorée :
- 13/158 threads ont >1 message sur KratOs (8.2%)
- Certains contenus liés passent sous le seuil 0.4 (ex: Node Config à 0.359)
- Pas de logging des décisions → debug difficile

### 8.1 Baisser le seuil de continuation

**Problème:** Le seuil 0.4 rejette du contenu lié (ex: 0.359 pour "Node Configuration")

**Solution:** Baisser à 0.35 pour les threads actifs, garder 0.5 pour suspended

**Fichier:** `intelligence/thread_manager.py`

**Changements:**
```python
# Ligne ~172 - Seuil actifs
if best_similarity > 0.35 and best_match:  # Était 0.4
    return ThreadDecision(CONTINUE, ...)

# Ligne ~184 - Seuil suspended (inchangé)
if similarity > 0.5:  # Reste 0.5
    return ThreadDecision(REACTIVATE, ...)
```

**Impact:** +10-15% de continuations attendues

---

### 8.2 Matching secondaire (topic exact)

**Problème:** Si embedding donne 0.34 mais qu'un topic est identique, on crée un nouveau thread

**Solution:** Boost de +0.15 si topic exact match

**Fichier:** `intelligence/thread_manager.py`

**Changements dans `_calculate_similarity()`:**
```python
def _calculate_similarity(self, content: str, extraction: Extraction, thread: Thread) -> float:
    # ... existing embedding calculation ...

    # Signal 2: Topic overlap
    topic_sim = 0.0
    exact_match_boost = 0.0

    if extraction.subjects and thread.topics:
        extraction_topics = set(s.lower() for s in extraction.subjects)
        thread_topics = set(t.lower() for t in thread.topics)
        common = extraction_topics & thread_topics

        if extraction_topics:
            topic_sim = len(common) / len(extraction_topics)

        # NOUVEAU: Boost si topic exact match
        if common:
            exact_match_boost = 0.15

    # Combine: 70% embedding, 30% topics, + boost
    combined = 0.7 * embedding_sim + 0.3 * topic_sim + exact_match_boost
    return min(combined, 1.0)  # Cap à 1.0
```

**Impact:** Contenus avec topic commun passent le seuil même si embedding faible

---

### 8.3 Logging structuré des décisions

**Problème:** Pas de visibilité sur pourquoi un thread est créé vs continué

**Solution:** Ajouter logging dans `_decide_action()` et `_calculate_similarity()`

**Fichier:** `intelligence/thread_manager.py`

**Changements:**
```python
import logging
logger = logging.getLogger(__name__)

def _decide_action(self, extraction: Extraction, content: str) -> ThreadDecision:
    active_threads = self.storage.threads.get_active()

    logger.info(f"DECIDE: {len(active_threads)} active threads")
    logger.debug(f"  Content preview: {content[:100]}...")

    # ... loop through threads ...
    for thread in active_threads:
        similarity = self._calculate_similarity(content, extraction, thread)
        if similarity > 0.3:  # Log candidates above noise threshold
            logger.info(f"  SIM: {similarity:.3f} → '{thread.title[:30]}'")

    # ... decision logic ...

    logger.info(f"DECIDE: {decision.action.value} → {decision.reason}")
    return decision
```

**Fichier:** `daemon/processor.py`

**Changements:**
```python
# Configurer logging au démarrage du daemon
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(self.log_file),
        logging.StreamHandler()
    ]
)
```

**Impact:** Logs détaillés dans `.ai/processor.log` pour debug

---

### 8.4 Commande `ai health`

**Problème:** Pas de moyen rapide de vérifier l'état du système

**Solution:** Nouvelle commande CLI qui affiche métriques clés

**Fichier:** `cli/commands/health.py` (nouveau)

```python
def run_health(ai_path: Path) -> int:
    """Display system health metrics."""
    threads = load_all_threads(ai_path)
    bridges = load_all_bridges(ai_path)

    # Métriques
    total_threads = len(threads)
    active = sum(1 for t in threads if t['status'] == 'active')
    suspended = sum(1 for t in threads if t['status'] == 'suspended')

    multi_msg = sum(1 for t in threads if len(t.get('messages', [])) > 1)
    continuation_rate = multi_msg / total_threads * 100 if total_threads else 0

    # Embeddings
    with_embedding = sum(1 for t in threads if t.get('embedding') and any(t['embedding']))
    embedding_coverage = with_embedding / total_threads * 100 if total_threads else 0

    # Daemon
    pid_file = ai_path / "processor.pid"
    daemon_running = pid_file.exists() and is_process_running(int(pid_file.read_text()))

    print("=== AI Smartness Health ===")
    print(f"Threads: {total_threads} ({active} active, {suspended} suspended)")
    print(f"Bridges: {len(bridges)}")
    print(f"Continuation rate: {continuation_rate:.1f}%")
    print(f"Embedding coverage: {embedding_coverage:.1f}%")
    print(f"Daemon: {'Running' if daemon_running else 'Stopped'}")

    # Warnings
    if continuation_rate < 10:
        print("⚠️  Low continuation rate - check thresholds")
    if embedding_coverage < 90:
        print("⚠️  Missing embeddings - run 'ai reindex'")

    return 0
```

**Fichier:** `cli/main.py`

**Changements:**
```python
# Ajouter parser
health_parser = subparsers.add_parser("health", help="System health check")

# Ajouter handler
elif args.command == "health":
    from .commands.health import run_health
    return run_health(ai_path)
```

---

### Fichiers à modifier/créer

| Fichier | Action | Description |
|---------|--------|-------------|
| `intelligence/thread_manager.py` | MODIFY | Seuil 0.35, topic boost, logging |
| `daemon/processor.py` | MODIFY | Config logging |
| `cli/commands/health.py` | CREATE | Commande health |
| `cli/main.py` | MODIFY | Ajouter health command |

---

### Ordre d'implémentation

1. **8.1 Seuil** (5 min) - Quick win, juste changer 0.4 → 0.35
2. **8.2 Topic boost** (15 min) - Modifier `_calculate_similarity()`
3. **8.3 Logging** (20 min) - Ajouter logger partout
4. **8.4 Health CLI** (30 min) - Nouveau fichier + intégration

---

### Vérification Phase 8

```bash
# Après déploiement sur KratOs:

# 1. Vérifier seuil appliqué
grep "0.35" /home/vzcrow/Dev/KratOs/ai_smartness/intelligence/thread_manager.py

# 2. Tester continuation avec contenu lié
# (faire des captures puis vérifier)
ai threads | head -10
# Devrait montrer plus de threads avec >1 message

# 3. Vérifier logs de décision
tail -50 /home/vzcrow/Dev/KratOs/ai_smartness/.ai/processor.log | grep "DECIDE"
# Devrait montrer les scores de similarité

# 4. Tester health
ai health
# Devrait afficher métriques + warnings
```

---

### Estimation Phase 8

| Tâche | Complexité | Temps estimé |
|-------|------------|--------------|
| 8.1 Seuil 0.35 | Triviale | 5 min |
| 8.2 Topic boost | Basse | 15 min |
| 8.3 Logging | Moyenne | 20 min |
| 8.4 Health CLI | Moyenne | 30 min |

**Total Phase 8:** ~70 min, 4 fichiers

---

### 8.5 Mise à jour documentation

**Fichiers à mettre à jour:**

| Fichier | Changements |
|---------|-------------|
| `SPEC_V2.md` | Ajouter section "Seuils de continuation" avec valeurs 0.35/0.5, documenter topic boost |
| `USER_GUIDE.md` | Ajouter commande `ai health`, section troubleshooting |
| `USER_GUIDE_fr.md` | Idem en français |
| `USER_GUIDE_es.md` | Idem en espagnol |
| `README.md` | Mettre à jour liste commandes CLI |
| `README_fr.md` | Idem en français |
| `README_es.md` | Idem en espagnol |
| `install.sh` | Ajouter `ai health` dans le message de fin d'installation |

**Contenu SPEC_V2.md - Section à ajouter:**

```markdown
## Seuils de continuation

| Contexte | Seuil | Description |
|----------|-------|-------------|
| Thread actif | 0.35 | Similarité minimale pour continuer un thread actif |
| Thread suspendu | 0.50 | Similarité minimale pour réactiver un thread |
| Topic boost | +0.15 | Bonus si topic exact match |

### Calcul de similarité

```
similarity = 0.7 * embedding_sim + 0.3 * topic_overlap + topic_boost
```

- `embedding_sim`: Cosine similarity entre embeddings TF-IDF/sentence-transformers
- `topic_overlap`: Ratio de topics communs
- `topic_boost`: +0.15 si au moins un topic identique
```

**Contenu USER_GUIDE - Section à ajouter:**

```markdown
## Commande `ai health`

Affiche les métriques de santé du système :

```bash
ai health
```

Output:
```
=== AI Smartness Health ===
Threads: 158 (100 active, 58 suspended)
Bridges: 3374
Continuation rate: 8.2%
Embedding coverage: 100.0%
Daemon: Running
```

### Interprétation

- **Continuation rate < 10%**: Les threads ne se consolident pas, vérifier les seuils
- **Embedding coverage < 90%**: Embeddings manquants, exécuter `ai reindex`
- **Daemon: Stopped**: Le daemon n'est pas actif, les captures ne sont pas traitées
```

**Contenu install.sh - Modifier le message de fin:**

```bash
# Après "Installation complete!", ajouter:
echo ""
echo "📊 CLI commands available:"
echo "   ai status    - Show memory status"
echo "   ai threads   - List threads"
echo "   ai bridges   - List bridges"
echo "   ai search    - Search threads"
echo "   ai reindex   - Recalculate embeddings"
echo "   ai health    - System health check"  # NOUVEAU
```

---

### Ordre d'implémentation (mise à jour)

1. **8.1 Seuil** (5 min)
2. **8.2 Topic boost** (15 min)
3. **8.3 Logging** (20 min)
4. **8.4 Health CLI** (30 min)
5. **8.5 Documentation** (30 min)

---

### Fichiers à modifier/créer (mise à jour)

| Fichier | Action | Description |
|---------|--------|-------------|
| `intelligence/thread_manager.py` | MODIFY | Seuil 0.35, topic boost, logging |
| `daemon/processor.py` | MODIFY | Config logging |
| `cli/commands/health.py` | CREATE | Commande health |
| `cli/main.py` | MODIFY | Ajouter health command |
| `SPEC_V2.md` | MODIFY | Documenter seuils et calcul similarité |
| `USER_GUIDE.md` | MODIFY | Ajouter health, troubleshooting |
| `USER_GUIDE_fr.md` | MODIFY | Idem FR |
| `USER_GUIDE_es.md` | MODIFY | Idem ES |
| `README.md` | MODIFY | Liste commandes CLI |
| `README_fr.md` | MODIFY | Idem FR |
| `README_es.md` | MODIFY | Idem ES |
| `install.sh` | MODIFY | Message fin avec health |

---

### Estimation Phase 8 (mise à jour)

| Tâche | Complexité | Temps estimé |
|-------|------------|--------------|
| 8.1 Seuil 0.35 | Triviale | 5 min |
| 8.2 Topic boost | Basse | 15 min |
| 8.3 Logging | Moyenne | 20 min |
| 8.4 Health CLI | Moyenne | 30 min |
| 8.5 Documentation | Basse | 30 min |

**Total Phase 8:** ~100 min, 12 fichiers

---

## Phase 8: COMPLÉTÉE ✓

- Seuil 0.35, topic boost, health CLI déployés
- Documentation mise à jour
- Fix daemon auto-start déployé

---

## Phase 9: Injection de Mémoire Réelle

### Problème identifié

Le hook `inject.py` capture les métadonnées mais **n'injecte pas** le contenu réel des threads dans les prompts de l'agent. Résultat : Claude "oublie" tout entre les sessions.

### État actuel (cassé)

```
Capture (PostToolUse) ──► Daemon ──► Threads DB ✓ (fonctionne)
                                          │
                                          ▼
Injection (UserPromptSubmit) ◄── inject.py (ne lit que métadonnées) ✗
```

### Objectif

```
UserPromptSubmit ──► inject.py ──► Lit threads pertinents
                                          │
                                          ▼
                                   Injecte résumé/contexte dans prompt
                                          │
                                          ▼
                                   Claude reçoit la mémoire ✓
```

### Ce qui doit être injecté

1. **Thread actif courant** : titre + résumé + derniers messages
2. **Threads liés** (via bridges) : titres + résumés courts
3. **Décisions en cours** : questions ouvertes, choix à faire
4. **Règles utilisateur** : "fais un plan avant chaque implémentation", etc.

### Contraintes

- **Performance** : Le hook doit être rapide (< 500ms)
- **Taille** : Injection limitée (~2000 chars max pour ne pas surcharger)
- **Pertinence** : Sélectionner les threads les plus pertinents par similarité

---

### 9.1 Créer `memory_retriever.py`

**Fichier** : `ai_smartness/intelligence/memory_retriever.py`

```python
class MemoryRetriever:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.embeddings = EmbeddingManager()

    def get_relevant_context(self, user_message: str, max_chars: int = 2000) -> str:
        """
        Récupère le contexte pertinent pour le message utilisateur.

        1. Embed le message
        2. Trouve les threads similaires
        3. Construit le résumé
        """

    def _find_similar_threads(self, message_embedding, limit: int = 5) -> List[Thread]:
        """Trouve les threads par similarité."""

    def _get_connected_threads(self, thread_id: str) -> List[Thread]:
        """Récupère les threads connectés via bridges."""

    def _build_context_string(self, threads: List[Thread], user_rules: List[str]) -> str:
        """Construit la chaîne de contexte à injecter."""
```

---

### 9.2 Modifier `inject.py`

**Fichier** : `ai_smartness/hooks/inject.py`

**Changements :**
1. Importer `MemoryRetriever`
2. Appeler `get_relevant_context(message)`
3. Injecter le contexte complet (pas juste les métadonnées)

```python
def main():
    # ... existing guard code ...

    message = get_message_from_stdin()

    # NOUVEAU: Récupérer la vraie mémoire
    from ..intelligence.memory_retriever import MemoryRetriever

    db_path = get_db_path()
    retriever = MemoryRetriever(db_path)
    memory_context = retriever.get_relevant_context(message)

    # Injecter dans le prompt
    if memory_context:
        injection = f"<system-reminder>\n{memory_context}\n</system-reminder>"
        augmented = f"{injection}\n\n{message}"
        print(json.dumps({"message": augmented}))
    else:
        print(json.dumps({"message": message}))
```

---

### 9.3 Format d'injection

```xml
<system-reminder>
AI Smartness Memory Context:

Current thread: "Phase 9 - Memory Injection"
Summary: Working on implementing real memory injection for Claude Code.

Related threads:
- "Daemon Auto-start Fix" - Fixed stderr logging
- "Thread Continuation Bug" - Hash randomization issue

User rules:
- "fais moi un plan avant chaque implementation"
- "pas de credits" (no co-author in commits)
</system-reminder>
```

---

### 9.4 Stocker les règles utilisateur

**Fichier** : `ai_smartness/.ai/user_rules.json`

```json
{
  "rules": [
    "fais moi un plan avant chaque implementation",
    "pas de credits"
  ],
  "last_updated": "2026-01-29T18:00:00"
}
```

**Détection automatique** : Dans `capture.py`, quand l'utilisateur dit :
- "toujours faire X"
- "règle: Y"
- "rappelle-toi que"
- "n'oublie pas"

→ Ajouter à `user_rules.json`

---

### Fichiers à créer/modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `intelligence/memory_retriever.py` | CREATE | Classe pour récupérer le contexte |
| `hooks/inject.py` | MODIFY | Utiliser MemoryRetriever |
| `hooks/capture.py` | MODIFY | Détecter et stocker les règles utilisateur |

---

### Ordre d'implémentation

1. **9.1** Créer `memory_retriever.py` avec logique de récupération (~60 lignes)
2. **9.2** Modifier `inject.py` pour utiliser le retriever (~20 lignes)
3. **9.3** Ajouter détection de règles dans `capture.py` (~30 lignes)
4. **9.4** Tester sur ai_smartness_dev
5. **9.5** Déployer sur KratOs

---

### Vérification Phase 9

```bash
# 1. Créer une règle utilisateur
# Dans une conversation: "rappelle-toi: toujours faire un plan"

# 2. Vérifier qu'elle est stockée
cat ai_smartness/.ai/user_rules.json

# 3. Vérifier les logs d'injection
cat ai_smartness/.ai/inject.log | tail -5
# Doit montrer l'injection avec le contexte mémoire

# 4. Tester la mémoire
# Poser une question sur le travail précédent
# L'agent doit se souvenir du contexte
```

---

### Risques et mitigations

| Risque | Mitigation |
|--------|------------|
| Hook trop lent | Limiter à 5 threads max, cache embeddings |
| Injection trop longue | Limite stricte 2000 chars, tronquer si nécessaire |
| Contexte non pertinent | Seuil similarité 0.3 minimum |
| Boucle infinie | Guard env var déjà en place |

---

### Estimation Phase 9

| Tâche | Lignes | Complexité |
|-------|--------|------------|
| 9.1 memory_retriever.py | ~80 | Moyenne |
| 9.2 inject.py modif | ~20 | Basse |
| 9.3 capture.py modif | ~30 | Basse |
| Tests & debug | - | Moyenne |

**Total Phase 9:** ~130 lignes de code, 3 fichiers

---

## Phase 10: Réactivation Hybride LLM

### Problème identifié

La réactivation actuelle utilise uniquement la similarité d'embeddings (cosine similarity), ce qui est purement statistique. Des relations sémantiques subtiles peuvent être manquées :

- "couche de meta cognition" ↔ "ai_smartness" → Faible similarité embedding mais relation évidente
- L'embedding ne capture pas toujours le contexte conceptuel

### Objectif

Implémenter une approche **hybride** où le LLM (Haiku) intervient pour les cas "borderline" afin d'améliorer la précision des décisions de réactivation.

### Architecture proposée

```
Message utilisateur
        ↓
   Embedding similarity
        ↓
┌───────┴───────────┐
│                   │
Sim > 0.35         0.15 < Sim < 0.35
(évident)          (borderline)
│                   │
↓                   ↓
Auto-reactivate    LLM Haiku décide
(sans LLM)         "Ce message concerne-t-il ce thread?"
                          │
                   ┌──────┴──────┐
                   │             │
                  OUI           NON
                   ↓             ↓
              Reactivate    Ignorer
```

### Seuils de décision

| Zone | Similarité | Action |
|------|------------|--------|
| Haute confiance | > 0.35 | Auto-réactivation (pas de LLM) |
| Borderline | 0.15 - 0.35 | LLM décide |
| Basse confiance | < 0.15 | Ignorer (pas de réactivation) |

### Prompt LLM pour décision de réactivation

```python
REACTIVATION_PROMPT = """
Tu es un assistant qui détermine si un message utilisateur est lié à un thread de mémoire existant.

MESSAGE UTILISATEUR:
{user_message}

THREAD CANDIDAT:
- Titre: {thread_title}
- Topics: {thread_topics}
- Résumé: {thread_summary}

QUESTION: Le message utilisateur concerne-t-il ce thread de mémoire?

Réponds UNIQUEMENT par un JSON:
{
  "related": true/false,
  "confidence": 0.0-1.0,
  "reason": "Explication courte"
}
"""
```

### Fichiers à créer/modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `intelligence/reactivation_decider.py` | CREATE | Nouvelle classe HybridReactivationDecider |
| `intelligence/memory_retriever.py` | MODIFY | Utiliser HybridReactivationDecider |
| `processing/extractor.py` | MODIFY | Ajouter méthode `decide_reactivation()` |
| `SPEC_V2.md` | MODIFY | Documenter l'approche hybride |
| `USER_GUIDE.md` | MODIFY | Section troubleshooting réactivation |
| `USER_GUIDE_fr.md` | MODIFY | Idem FR |
| `USER_GUIDE_es.md` | MODIFY | Idem ES |

---

### 10.1 Créer `reactivation_decider.py`

**Fichier** : `ai_smartness/intelligence/reactivation_decider.py`

```python
"""
Hybrid Reactivation Decider - Uses LLM for borderline cases.

This module decides whether to reactivate suspended threads
using a combination of embedding similarity and LLM reasoning.
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReactivationDecision:
    """Result of a reactivation decision."""
    should_reactivate: bool
    confidence: float
    reason: str
    used_llm: bool  # Whether LLM was consulted


class HybridReactivationDecider:
    """
    Decides thread reactivation using hybrid approach.

    - High similarity (>0.35): Auto-reactivate without LLM
    - Borderline (0.15-0.35): Consult LLM
    - Low similarity (<0.15): Don't reactivate
    """

    # Thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.35
    BORDERLINE_THRESHOLD = 0.15

    def __init__(self, extractor=None):
        """
        Initialize with optional LLM extractor.

        Args:
            extractor: LLMExtractor instance (lazy loaded if None)
        """
        self._extractor = extractor

    @property
    def extractor(self):
        """Lazy load extractor."""
        if self._extractor is None:
            from ..processing.extractor import LLMExtractor
            self._extractor = LLMExtractor()
        return self._extractor

    def decide(
        self,
        user_message: str,
        thread: Dict[str, Any],
        similarity: float
    ) -> ReactivationDecision:
        """
        Decide whether to reactivate a suspended thread.

        Args:
            user_message: The user's current message
            thread: Thread dict with title, topics, summary
            similarity: Pre-calculated embedding similarity

        Returns:
            ReactivationDecision with should_reactivate, confidence, reason
        """
        # High confidence: Auto-reactivate
        if similarity > self.HIGH_CONFIDENCE_THRESHOLD:
            return ReactivationDecision(
                should_reactivate=True,
                confidence=similarity,
                reason=f"High similarity ({similarity:.2f})",
                used_llm=False
            )

        # Low confidence: Don't reactivate
        if similarity < self.BORDERLINE_THRESHOLD:
            return ReactivationDecision(
                should_reactivate=False,
                confidence=1.0 - similarity,
                reason=f"Low similarity ({similarity:.2f})",
                used_llm=False
            )

        # Borderline: Consult LLM
        return self._llm_decide(user_message, thread, similarity)

    def _llm_decide(
        self,
        user_message: str,
        thread: Dict[str, Any],
        similarity: float
    ) -> ReactivationDecision:
        """Use LLM to decide borderline cases."""
        prompt = self._build_prompt(user_message, thread)

        try:
            response = self.extractor._call_llm(prompt)
            result = json.loads(response)

            related = result.get("related", False)
            llm_confidence = result.get("confidence", 0.5)
            reason = result.get("reason", "LLM decision")

            # Combine embedding similarity with LLM confidence
            final_confidence = (similarity + llm_confidence) / 2

            logger.info(
                f"LLM decision for '{thread.get('title', 'Unknown')[:30]}': "
                f"related={related}, conf={llm_confidence:.2f}"
            )

            return ReactivationDecision(
                should_reactivate=related,
                confidence=final_confidence,
                reason=f"LLM: {reason}",
                used_llm=True
            )

        except Exception as e:
            logger.warning(f"LLM decision failed, using similarity: {e}")
            # Fallback to similarity-based decision
            return ReactivationDecision(
                should_reactivate=similarity > 0.25,  # Middle of borderline
                confidence=similarity,
                reason=f"Fallback (LLM failed): similarity={similarity:.2f}",
                used_llm=False
            )

    def _build_prompt(self, user_message: str, thread: Dict[str, Any]) -> str:
        """Build the LLM prompt for reactivation decision."""
        title = thread.get("title", "Sans titre")
        topics = ", ".join(thread.get("topics", [])[:5])
        summary = thread.get("summary", "")[:200]

        return f"""Tu détermines si un message utilisateur est lié à un thread de mémoire.

MESSAGE UTILISATEUR:
{user_message[:500]}

THREAD CANDIDAT:
- Titre: {title}
- Topics: {topics}
- Résumé: {summary if summary else "(aucun)"}

Le message concerne-t-il ce thread? Réponds UNIQUEMENT en JSON:
{{"related": true/false, "confidence": 0.0-1.0, "reason": "explication courte"}}"""
```

---

### 10.2 Modifier `memory_retriever.py`

**Intégration du HybridReactivationDecider** :

```python
# Dans _find_similar_threads(), remplacer la logique de réactivation actuelle

from .reactivation_decider import HybridReactivationDecider

# Dans __init__
self._decider = None

@property
def decider(self):
    if self._decider is None:
        self._decider = HybridReactivationDecider()
    return self._decider

# Dans la boucle de résultats (remplace le bloc actuel)
for item in scored_threads[:limit]:
    thread = item["thread"]
    similarity = item["similarity"]

    # Use hybrid decider for suspended threads
    if thread.get("status") == "suspended":
        decision = self.decider.decide(message, thread, similarity)

        if decision.should_reactivate:
            self._reactivate_thread(thread)
            thread["status"] = "active"
            logger.info(
                f"Reactivated: {thread.get('title')} "
                f"(conf={decision.confidence:.2f}, llm={decision.used_llm})"
            )

    result_threads.append(thread)
```

---

### 10.3 Mise à jour SPEC_V2.md

**Ajouter section** :

```markdown
## Réactivation Hybride LLM

### Principe

La réactivation des threads suspendus utilise une approche hybride combinant :
1. **Similarité d'embeddings** (rapide, gratuit)
2. **Raisonnement LLM** (précis, pour cas borderline)

### Zones de décision

| Similarité | Action | LLM utilisé |
|------------|--------|-------------|
| > 0.35 | Auto-réactivation | Non |
| 0.15 - 0.35 | Décision LLM | Oui (Haiku) |
| < 0.15 | Pas de réactivation | Non |

### Avantages

- **Performance** : LLM appelé uniquement pour ~20% des cas (borderline)
- **Précision** : Relations sémantiques subtiles capturées
- **Économie** : Haiku économique (~$0.00025/appel)

### Exemple

```
Message: "où en est la couche de meta cognition?"

Thread suspendu: "Spécification AI Smartness v2"
Similarité embedding: 0.28 (borderline)

→ LLM consulté
→ Décision: related=true, confidence=0.85
→ Thread réactivé
```
```

---

### 10.4 Mise à jour documentation utilisateur

**USER_GUIDE.md** - Ajouter section :

```markdown
## Réactivation automatique des threads

AI Smartness réactive automatiquement les threads suspendus quand vous mentionnez un sujet lié.

### Comment ça fonctionne

1. **Analyse de votre message** : Calcul de similarité avec les threads suspendus
2. **Décision intelligente** : Pour les cas incertains, un LLM rapide (Haiku) vérifie la relation sémantique
3. **Réactivation** : Le thread pertinent redevient actif et son contexte est injecté

### Exemple

Si vous avez travaillé sur "système de mémoire IA" hier (thread suspendu), et aujourd'hui vous demandez :
> "rappelle-moi comment fonctionne la couche de meta cognition"

Le système :
1. Détecte la similarité avec le thread "Système de mémoire IA"
2. Consulte Haiku qui confirme la relation sémantique
3. Réactive le thread
4. Injecte le contexte dans votre conversation

### Commande de diagnostic

```bash
ai health
```

Affiche le taux de réactivation et le nombre d'appels LLM.
```

---

### Ordre d'implémentation

1. **10.1** Créer `reactivation_decider.py` (~100 lignes)
2. **10.2** Modifier `memory_retriever.py` (~30 lignes changées)
3. **10.3** Mettre à jour `SPEC_V2.md`
4. **10.4** Mettre à jour `USER_GUIDE.md`, `USER_GUIDE_fr.md`, `USER_GUIDE_es.md`
5. **10.5** Tester sur ai_smartness_dev
6. **10.6** Déployer sur KratOs via install.sh

---

### Vérification Phase 10

```bash
# 1. Vérifier que le decider fonctionne
cd /home/vzcrow/Dev/KratOs && python3 -c "
from ai_smartness.intelligence.reactivation_decider import HybridReactivationDecider

decider = HybridReactivationDecider()
thread = {'title': 'AI Smartness', 'topics': ['memory', 'llm'], 'summary': 'Meta cognition layer'}
decision = decider.decide('couche meta cognition', thread, similarity=0.25)
print(f'Should reactivate: {decision.should_reactivate}')
print(f'Used LLM: {decision.used_llm}')
print(f'Reason: {decision.reason}')
"

# 2. Tester avec une vraie injection
echo '{"message": "parle moi de la couche meta cognition"}' | python3 ai_smartness/hooks/inject.py

# 3. Vérifier les logs
grep "LLM decision" ai_smartness/.ai/inject.log | tail -5
```

---

### Risques et mitigations

| Risque | Mitigation |
|--------|------------|
| LLM timeout | Fallback sur similarité seule après 5s |
| Coût API | Haiku économique, seulement ~20% des cas |
| Latence ajoutée | ~1-2s pour borderline seulement |
| LLM indisponible | Fallback automatique |

---

### Estimation Phase 10

| Tâche | Lignes | Complexité |
|-------|--------|------------|
| 10.1 reactivation_decider.py | ~100 | Moyenne |
| 10.2 memory_retriever.py modif | ~30 | Basse |
| 10.3-10.4 Documentation | ~100 | Basse |
| Tests & debug | - | Moyenne |

**Total Phase 10:** ~230 lignes de code/doc, 5 fichiers

---

## Phase 11: Capture des Prompts Utilisateur

### Problème identifié

Le système actuel ne capture que les **résultats d'outils** (Read, Bash, etc.) via `capture.py`. Les **discussions conversationnelles** (prompts utilisateur) ne sont jamais traitées par le daemon.

**Conséquence:** Si l'utilisateur discute d'un sujet sans lire de fichiers, aucun thread n'est créé. La mémoire ne contient que les lectures de fichiers, pas le contexte conversationnel.

### Preuve du problème

Sur KratOs, après discussion sur ai_smartness ET lecture de fichiers KratOs :
- 2 threads créés (100% KratOs via Read)
- 0 thread ai_smartness (discussions ignorées)

Le `capture.log` ne montre que des événements `[Read]` - aucun prompt utilisateur.

### État actuel (cassé)

```
User Message ──► inject.py ──► Injecte contexte ✓
                            ──► NE CAPTURE PAS ✗

Tool Result ──► capture.py ──► Daemon ──► Thread ✓
```

### Solution proposée

```
User Message ──► inject.py ──► 1. Injecte contexte ✓
                            ──► 2. Envoie au daemon (NOUVEAU) ✓
                                        │
                                        ▼
                                   Thread créé
```

### Architecture de la solution

**Modification minimale** : Réutiliser l'infrastructure existante

1. `inject.py` importe déjà les fonctions de path et log
2. Le daemon accepte déjà tout type de source (défaut: "prompt")
3. L'extractor a déjà un prompt pour source_type="prompt"

**Seule modification nécessaire** : Ajouter l'envoi au daemon dans `inject.py`

---

### 11.1 Modifier `hooks/inject.py`

**Fichier** : `src/ai_smartness/hooks/inject.py`

**Changements** :

```python
# Après la fonction get_memory_context(), ajouter:

def send_prompt_to_daemon(message: str, ai_path: Path) -> bool:
    """
    Send user prompt to daemon for thread processing.

    Args:
        message: User message
        ai_path: Path to .ai directory

    Returns:
        True if sent successfully
    """
    try:
        # Import daemon client (same as capture.py)
        package_root = get_package_root()
        sys.path.insert(0, str(package_root.parent))

        from ai_smartness.daemon.client import send_capture_with_retry

        # Send with tool="UserPrompt" (processor defaults to source_type="prompt")
        return send_capture_with_retry(ai_path, {
            "tool": "UserPrompt",
            "content": message
        })

    except Exception as e:
        log(f"Failed to send prompt to daemon: {e}")
        return False


# Dans main(), après get_memory_context(), ajouter:

def main():
    # ... existing guard code ...

    message = get_message_from_stdin()

    if not message:
        print(json.dumps({"continue": True}))
        return

    db_path = get_db_path()
    ai_path = db_path.parent

    # NOUVEAU: Envoyer le prompt au daemon pour capture
    # (async, non-bloquant car fire-and-forget via socket)
    if len(message) > 50:  # Ignorer les messages très courts
        send_prompt_to_daemon(message, ai_path)
        log(f"Sent prompt to daemon: {len(message)} chars")

    # ... rest of existing code (memory context, injection) ...
```

---

### 11.2 Filtrage des prompts

**Problème potentiel** : Tous les prompts ne méritent pas un thread

**Solution** : Filtrer les prompts trop courts ou répétitifs

```python
# Dans send_prompt_to_daemon ou avant l'appel:

MIN_PROMPT_LENGTH = 50  # Minimum chars pour créer un thread
SKIP_PATTERNS = [
    r"^(ok|oui|non|yes|no|d'accord|bien)$",  # Acquiescements
    r"^[\.!?]+$",  # Ponctuation seule
    r"^(merci|thanks|gracias)$",  # Remerciements
]

def should_capture_prompt(message: str) -> bool:
    """Check if prompt should be captured."""
    if len(message) < MIN_PROMPT_LENGTH:
        return False

    message_lower = message.lower().strip()
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, message_lower, re.IGNORECASE):
            return False

    return True
```

---

### 11.3 Éviter les doublons

**Problème** : Le même sujet peut être discuté puis lu dans un fichier

**Solution** : Le système existant gère déjà ça via `_calculate_similarity()` - si un thread similaire existe, le nouveau contenu y est ajouté au lieu de créer un doublon.

---

### Fichiers à modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `hooks/inject.py` | MODIFY | Ajouter envoi au daemon + filtrage |

**Un seul fichier modifié** - réutilisation maximale de l'infrastructure.

---

### Vérification Phase 11

```bash
# 1. Avant fix: vérifier qu'aucun prompt n'est capturé
grep "UserPrompt" /path/to/ai_smartness/.ai/capture.log
# Aucun résultat

# 2. Après fix: envoyer un message de discussion
# (pas de Read, juste conversation)
# "parle-moi du système de réactivation hybride"

# 3. Vérifier la capture
cat /path/to/ai_smartness/.ai/inject.log | tail -5
# Doit montrer "Sent prompt to daemon: XXX chars"

# 4. Vérifier le thread créé
ai threads | grep -i "reactivation"
# Doit montrer un nouveau thread sur le sujet discuté

# 5. Test de délimitation
# Discuter d'un sujet A (ex: ai_smartness)
# Puis d'un sujet B (ex: KratOs)
# Vérifier que 2 threads distincts sont créés
ai threads
```

---

### Risques et mitigations

| Risque | Mitigation |
|--------|------------|
| Performance | Socket non-bloquant, fire-and-forget |
| Prompts trop courts | Filtre MIN_PROMPT_LENGTH=50 |
| Doublons | Similarité existante les évite |
| Boucle infinie | Guard HOOK_GUARD_ENV existant |

---

### Estimation Phase 11

| Tâche | Lignes | Complexité |
|-------|--------|------------|
| send_prompt_to_daemon() | ~25 | Basse |
| should_capture_prompt() | ~15 | Basse |
| Intégration dans main() | ~10 | Triviale |
| Tests | - | Basse |

**Total Phase 11:** ~50 lignes, 1 fichier modifié

---

### Ordre d'implémentation

1. Ajouter `send_prompt_to_daemon()` dans inject.py
2. Ajouter `should_capture_prompt()` pour filtrage
3. Appeler dans `main()` après récupération du message
4. Commit (pas de push automatique)
5. User décide du push après validation locale sur KratOs

---

## Phase 12: Fix Pollution Prompts LLM Internes

### Problème identifié (Phase 11)

Après implémentation de la capture de prompts utilisateur dans `inject.py`, les threads sont pollués par les **prompts LLM internes** (extractor, synthesis, reactivation_decider).

**Exemple de pollution sur KratOs :**
- Thread créé avec titre: "Pas de texte hors du JSON"
- Summary contient: "Analyse ce message utilisateur..." (le prompt de l'extractor)
- Ce n'est PAS le vrai message utilisateur, c'est le prompt interne

**Cause racine :**
Les appels `claude --print` dans `extractor.py`, `synthesis.py` et `reactivation_decider.py` déclenchent le hook `UserPromptSubmit` → `inject.py` capture le prompt LLM au lieu du vrai prompt utilisateur.

**Pourquoi l'approche env var échoue :**
- Les hooks sont lancés comme processus **séparés** par Claude CLI
- Les variables d'environnement (`CLAUDE_INTERNAL_CALL=1`) ne se propagent pas du subprocess vers le hook

---

### 12.1 Solution : Fichier Lock Temporaire

**Principe :** Utiliser un fichier lock partagé entre processus (contrairement aux env vars).

```
AVANT appel LLM interne:
  → Créer .ai/internal_call.lock (avec timestamp)

DANS inject.py:
  → Si .ai/internal_call.lock existe ET récent (< 10s) → SKIP capture

APRÈS appel LLM interne:
  → Supprimer .ai/internal_call.lock
```

**Avantages :**
- Fonctionne entre processus (fichiers partagés)
- Simple à implémenter
- Fallback automatique (fichier expire après 10s)
- Pas de changement d'architecture majeur

---

### 12.2 Fichiers à modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `processing/extractor.py` | MODIFY | Ajouter lock avant/après `_call_llm()` |
| `intelligence/synthesis.py` | MODIFY | Ajouter lock avant/après `_call_llm()` |
| `hooks/inject.py` | MODIFY | Vérifier le fichier lock dans `should_capture_prompt()` |

---

### 12.3 Implémentation détaillée

#### 12.3.1 Fonction utilitaire de lock (à ajouter dans chaque fichier ou module commun)

```python
import time
from pathlib import Path

def get_lock_path(ai_path: Path) -> Path:
    """Get the internal call lock file path."""
    return ai_path / "internal_call.lock"

def acquire_internal_lock(ai_path: Path) -> bool:
    """Create lock file before internal LLM call."""
    try:
        lock_path = get_lock_path(ai_path)
        lock_path.write_text(str(time.time()))
        return True
    except Exception:
        return False

def release_internal_lock(ai_path: Path):
    """Remove lock file after internal LLM call."""
    try:
        lock_path = get_lock_path(ai_path)
        if lock_path.exists():
            lock_path.unlink()
    except Exception:
        pass

def is_internal_call_active(ai_path: Path, max_age: float = 10.0) -> bool:
    """Check if an internal LLM call is in progress."""
    try:
        lock_path = get_lock_path(ai_path)
        if not lock_path.exists():
            return False

        # Check age
        timestamp = float(lock_path.read_text().strip())
        age = time.time() - timestamp

        # Lock too old = stale, ignore
        if age > max_age:
            lock_path.unlink()  # Clean up stale lock
            return False

        return True
    except Exception:
        return False
```

#### 12.3.2 Modification de `extractor.py`

```python
def _call_llm(self, prompt: str) -> str:
    """Call Claude LLM with prompt."""
    import os
    from pathlib import Path

    # Acquire lock before call
    ai_path = self._get_ai_path()  # Méthode à ajouter
    if ai_path:
        acquire_internal_lock(ai_path)

    try:
        # ... existing subprocess call ...
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() if result.returncode == 0 else self._fallback_extraction(prompt)
    finally:
        # Always release lock
        if ai_path:
            release_internal_lock(ai_path)
```

#### 12.3.3 Modification de `inject.py`

```python
def should_capture_prompt(message: str) -> bool:
    """Check if prompt should be captured."""
    # Check file-based lock (works across processes)
    ai_path = get_db_path().parent
    if is_internal_call_active(ai_path):
        log("[SKIP] Internal LLM call detected via lock file")
        return False

    # ... rest of existing checks ...
```

---

### 12.4 Revert des modifications défaillantes

**Supprimer de `extractor.py` :**
- Lignes 291-293 : `env = os.environ.copy()` / `env['CLAUDE_INTERNAL_CALL'] = '1'`
- Ligne 302 : `env=env` dans subprocess.run

**Supprimer de `synthesis.py` :**
- Lignes 219-221 : idem

**Supprimer de `inject.py` :**
- Lignes 421-423 : check `CLAUDE_INTERNAL_CALL` env var (remplacer par check fichier lock)

---

### 12.5 Ordre d'implémentation

1. Créer fonction utilitaire `acquire_internal_lock()` / `release_internal_lock()` / `is_internal_call_active()`
2. Modifier `extractor.py` : ajouter lock dans `_call_llm()` + retirer env var
3. Modifier `synthesis.py` : idem
4. Modifier `inject.py` : remplacer check env var par check fichier lock
5. Tester sur KratOs
6. Commit (pas de push automatique)

---

### 12.6 Vérification Phase 12

```bash
# 1. Vérifier que le lock est créé pendant un appel LLM
# Lancer une extraction en background et vérifier:
ls -la ai_smartness/.ai/internal_call.lock

# 2. Tester qu'aucun prompt LLM n'est capturé
# Conversation normale → vérifier inject.log
grep "Internal LLM call detected" ai_smartness/.ai/inject.log

# 3. Vérifier que les VRAIS prompts utilisateur sont capturés
grep "UserPrompt" ai_smartness/.ai/inject.log | tail -5
# Doit montrer les vrais messages, pas "Analyse ce message..."

# 4. Vérifier threads créés (pas de pollution)
ai threads | head -5
# Titres doivent être significatifs, pas "Pas de texte hors du JSON"
```

---

### 12.7 Risques et mitigations

| Risque | Mitigation |
|--------|------------|
| Lock file non supprimé (crash) | Expiration automatique après 10s |
| Race condition | Acceptable car hooks sont séquentiels |
| Performance | Opérations fichier rapides (<1ms) |

---

### 12.8 Estimation Phase 12

| Tâche | Lignes | Complexité |
|-------|--------|------------|
| Fonctions lock | ~30 | Basse |
| extractor.py modif | ~15 | Basse |
| synthesis.py modif | ~15 | Basse |
| inject.py modif | ~10 | Basse |
| Tests | - | Moyenne |

**Total Phase 12:** ~70 lignes, 3 fichiers modifiés

---

## Phase 13: Capture Task + Filtrage LLM Intelligent

### Problème identifié

1. **Task filtré** : Les résultats de sous-agents (exploration, recherche) sont rejetés car leur JSON commence par `{"retrieval_status":...}`
2. **Filtrage heuristique limité** : Les règles statiques (préfixes JSON) ne distinguent pas le contenu utile du bruit

### Objectif

- Capturer les résultats Task qui contiennent de l'information sémantique utile
- Utiliser Haiku pour extraire/synthétiser le contenu pertinent
- Filtrer intelligemment le bruit technique (JSON metadata, statuts, etc.)

---

### 13.1 Architecture proposée

```
Tool Output (Task, Bash, etc.)
        ↓
┌───────────────────────────────────┐
│ Étape 1: Pré-filtrage rapide      │
│ - Trop court (<50 chars)? → SKIP  │
│ - Dans skip_tools? → SKIP         │
│ - Sinon → continuer               │
└───────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│ Étape 2: Extraction contenu       │
│ - Task: parser JSON, extraire     │
│   "content" ou "output"           │
│ - Bash: extraire stdout si utile  │
└───────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│ Étape 3: Filtrage LLM (Haiku)     │
│ - "Ce contenu est-il informatif?" │
│ - Score 0-1 + résumé condensé     │
│ - Seuil: 0.5 pour capturer        │
└───────────────────────────────────┘
        ↓
   Daemon → Thread
```

---

### 13.2 Modification `capture.py`

**Fichier** : `src/ai_smartness/hooks/capture.py`

#### 13.2.1 Retirer Task du filtre noise

```python
# AVANT (ligne 82)
json_noise_prefixes = [
    "{'filePath':", '{"filePath":',      # Edit tool
    "{'stdout':", '{"stdout":',           # Bash tool
    "{'newTodos':", '{"newTodos":',       # TodoWrite
    "{'retrieval_status':", '{"retrieval_status":',  # Task output  ← SUPPRIMER
    "{'oldTodos':", '{"oldTodos":',       # TodoWrite
    "{'continue':", '{"continue":',       # Hook output
]

# APRÈS
json_noise_prefixes = [
    "{'filePath':", '{"filePath":',      # Edit tool
    "{'newTodos':", '{"newTodos":',       # TodoWrite
    "{'oldTodos':", '{"oldTodos":',       # TodoWrite
    "{'continue':", '{"continue":',       # Hook output
    # Task et Bash retirés - traités par LLM
]
```

#### 13.2.2 Ajouter extraction Task

```python
def extract_task_content(raw_output: str) -> Optional[str]:
    """
    Extract useful content from Task tool JSON output.

    Task output format:
    {"retrieval_status": "...", "content": "actual useful text", ...}

    Returns:
        Extracted content or None if nothing useful
    """
    try:
        data = json.loads(raw_output)

        # Chercher le contenu utile dans différents champs
        content_fields = ['content', 'output', 'result', 'text', 'message']

        for field in content_fields:
            if field in data and data[field]:
                content = str(data[field])
                if len(content) > 50:  # Minimum utile
                    return content

        # Si pas de champ connu, chercher la plus longue string
        longest = ""
        for key, value in data.items():
            if isinstance(value, str) and len(value) > len(longest):
                if key not in ['retrieval_status', 'status', 'type']:
                    longest = value

        return longest if len(longest) > 50 else None

    except json.JSONDecodeError:
        # Pas du JSON, retourner tel quel si assez long
        return raw_output if len(raw_output) > 50 else None
```

---

### 13.3 Nouveau module `processing/llm_filter.py`

**Fichier** : `src/ai_smartness/processing/llm_filter.py`

```python
"""
LLM-based content filter using Haiku for fast, cheap filtering.

Determines if tool output contains useful semantic information
worth capturing in the memory system.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of LLM filtering."""
    should_capture: bool
    relevance_score: float  # 0.0 - 1.0
    summary: str  # Condensed version if captured
    reason: str  # Why captured or rejected


FILTER_PROMPT = '''Tu es un filtre de contenu pour un système de mémoire IA.

CONTENU À ANALYSER:
{content}

SOURCE: {source_type}

QUESTION: Ce contenu contient-il de l'information sémantique utile à mémoriser?

Critères pour CAPTURER (score > 0.5):
- Explications techniques, décisions, architecture
- Questions posées, problèmes identifiés
- Résultats de recherche avec insights
- Code avec contexte explicatif

Critères pour REJETER (score < 0.5):
- Métadonnées techniques (JSON brut, statuts)
- Listes de fichiers sans contexte
- Erreurs/logs sans explication
- Contenu trop fragmenté

Réponds UNIQUEMENT en JSON:
{{"capture": true/false, "score": 0.0-1.0, "summary": "résumé si capture", "reason": "explication courte"}}'''


class LLMContentFilter:
    """
    Uses Haiku to intelligently filter tool outputs.

    Fast and cheap (~$0.00025/call) for high-volume filtering.
    """

    # Seuil de capture
    CAPTURE_THRESHOLD = 0.5

    # Limite de contenu à analyser (tokens économie)
    MAX_CONTENT_LENGTH = 2000

    def __init__(self, extractor=None):
        """
        Initialize with optional LLM extractor.

        Args:
            extractor: LLMExtractor instance (lazy loaded if None)
        """
        self._extractor = extractor

    @property
    def extractor(self):
        """Lazy load extractor with Haiku model."""
        if self._extractor is None:
            from .extractor import LLMExtractor
            # Force Haiku pour le filtrage (rapide + économique)
            self._extractor = LLMExtractor(model="claude-haiku-3-5-20250620")
        return self._extractor

    def filter(self, content: str, source_type: str) -> FilterResult:
        """
        Filter content using LLM.

        Args:
            content: Raw content to filter
            source_type: Source type (task, bash, etc.)

        Returns:
            FilterResult with decision and summary
        """
        # Pré-filtrage rapide (éviter appel LLM inutile)
        if len(content.strip()) < 50:
            return FilterResult(
                should_capture=False,
                relevance_score=0.0,
                summary="",
                reason="Too short"
            )

        # Tronquer si trop long
        truncated = content[:self.MAX_CONTENT_LENGTH]
        if len(content) > self.MAX_CONTENT_LENGTH:
            truncated += "\n[... truncated ...]"

        # Appeler LLM
        prompt = FILTER_PROMPT.format(
            content=truncated,
            source_type=source_type
        )

        try:
            response = self.extractor._call_llm(prompt)
            result = json.loads(response)

            score = float(result.get("score", 0.0))
            should_capture = result.get("capture", False) and score >= self.CAPTURE_THRESHOLD

            return FilterResult(
                should_capture=should_capture,
                relevance_score=score,
                summary=result.get("summary", "")[:500] if should_capture else "",
                reason=result.get("reason", "LLM decision")
            )

        except Exception as e:
            logger.warning(f"LLM filter failed, using fallback: {e}")
            # Fallback: capturer si assez long et pas JSON pur
            is_useful = len(content) > 100 and not content.strip().startswith('{')
            return FilterResult(
                should_capture=is_useful,
                relevance_score=0.5 if is_useful else 0.2,
                summary=content[:200] if is_useful else "",
                reason=f"Fallback (LLM failed): {e}"
            )

    def filter_batch(self, items: list) -> list:
        """
        Filter multiple items (future optimization with batching).

        Args:
            items: List of (content, source_type) tuples

        Returns:
            List of FilterResult
        """
        return [self.filter(content, source_type) for content, source_type in items]
```

---

### 13.4 Intégration dans `capture.py`

**Modification de `process_capture()`** :

```python
def process_capture(tool_name: str, output: str, file_path: Optional[str] = None):
    """
    Process a tool output for capture.

    Now includes LLM filtering for Task and other noisy tools.
    """
    # 1. Extraction spéciale pour Task
    if tool_name == "Task":
        extracted = extract_task_content(output)
        if not extracted:
            log(f"[{tool_name}] No useful content extracted from Task JSON")
            return
        output = extracted

    # 2. Pré-filtrage heuristique (inchangé pour les autres)
    cleaned, should_process = filter_noise(output)
    if not should_process:
        log(f"[{tool_name}] Filtered by heuristics")
        return

    # 3. Filtrage LLM pour Task et Bash (outils potentiellement bruyants)
    noisy_tools = ['Task', 'Bash']
    if tool_name in noisy_tools:
        from ..processing.llm_filter import LLMContentFilter

        llm_filter = LLMContentFilter()
        result = llm_filter.filter(cleaned, tool_name.lower())

        if not result.should_capture:
            log(f"[{tool_name}] Rejected by LLM: {result.reason} (score={result.relevance_score:.2f})")
            return

        # Utiliser le résumé LLM si disponible
        if result.summary:
            cleaned = result.summary
            log(f"[{tool_name}] LLM summarized: {len(result.summary)} chars (score={result.relevance_score:.2f})")

    # 4. Envoyer au daemon (inchangé)
    ai_path = get_ai_path()
    success = send_to_daemon(ai_path, {
        "tool": tool_name,
        "content": cleaned,
        "file_path": file_path
    })

    if success:
        log(f"[{tool_name}] Sent to daemon: {len(cleaned)} chars")
    else:
        log(f"[{tool_name}] Failed to send to daemon")
```

---

### 13.5 Optimisation performance

**Problème potentiel** : Appel LLM à chaque capture = latence

**Solutions** :

1. **Cache local** : Hash du contenu → résultat (évite re-filtrage)
2. **Batch processing** : Le daemon accumule et filtre par lots
3. **Async** : Filtrage non-bloquant, capture async

**Implémentation cache simple** :

```python
# Dans LLMContentFilter

import hashlib
from functools import lru_cache

@lru_cache(maxsize=100)
def _cached_filter(self, content_hash: str, content: str, source_type: str) -> FilterResult:
    return self._do_filter(content, source_type)

def filter(self, content: str, source_type: str) -> FilterResult:
    # Hash pour cache
    content_hash = hashlib.md5(content[:500].encode()).hexdigest()
    return self._cached_filter(content_hash, content, source_type)
```

---

### 13.6 Fichiers à créer/modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `processing/llm_filter.py` | CREATE | Nouveau module de filtrage LLM |
| `hooks/capture.py` | MODIFY | Intégrer extraction Task + filtrage LLM |

---

### 13.7 Vérification Phase 13

```bash
# 1. Vérifier que Task n'est plus filtré automatiquement
grep "retrieval_status" src/ai_smartness/hooks/capture.py
# Ne doit plus être dans json_noise_prefixes

# 2. Tester capture Task (lancer un sous-agent explore)
# Vérifier les logs
tail -20 ai_smartness/.ai/capture.log | grep Task
# Doit montrer "LLM summarized" ou "Rejected by LLM"

# 3. Vérifier thread créé depuis Task
ai threads | head -5
# Devrait contenir des threads issus d'exploration

# 4. Tester performance
time echo '{"message": "test"}' | python3 ai_smartness/hooks/capture.py
# Doit rester < 2s même avec LLM
```

---

### 13.8 Risques et mitigations

| Risque | Mitigation |
|--------|------------|
| Latence LLM | Cache + async + seulement pour Task/Bash |
| Coût API | Haiku très économique (~$0.00025/appel) |
| LLM indisponible | Fallback heuristique existant |
| Sur-filtrage | Seuil 0.5 conservateur, ajustable |

---

### 13.9 Estimation Phase 13

| Tâche | Lignes | Complexité |
|-------|--------|------------|
| `llm_filter.py` | ~120 | Moyenne |
| `capture.py` modif | ~50 | Moyenne |
| Cache/optim | ~30 | Basse |
| Tests | - | Moyenne |

**Total Phase 13:** ~200 lignes, 2 fichiers

---

### 13.10 Ordre d'implémentation

1. Créer `processing/llm_filter.py` avec classe LLMContentFilter
2. Ajouter `extract_task_content()` dans capture.py
3. Retirer Task de json_noise_prefixes
4. Intégrer filtrage LLM dans process_capture()
5. Ajouter cache simple
6. Commit (pas de push automatique)
7. User teste sur KratOs
