#!/bin/bash
#
# AI Smartness Installation Script (v6.2.1)
# Simplified architecture with absolute paths
# Includes migration from ai_smartness_v2 to ai_smartness
#
# v6.2: Phase 3 - Advanced Shared Cognition
# - ai_recommend: Subscription recommendations based on topic similarity
# - ai_topics: Network-wide topic discovery and cross-agent overlap
# - Shared Context Injection: Subscribed threads auto-injected in recall context
# - Bridge Strength: Cross-agent usage tracking (cross_agent_uses)
#
# v6.1: Bridge Management Suite
# - ai_bridges: List/filter ThinkBridges
# - ai_bridge_analysis: Bridge network analytics
#
# v6.0: Shared Cognition Protocol
# - SharedThread: Publish threads to network for inter-agent sharing
# - Subscription: Subscribe to SharedThreads from other agents
# - InterAgentBridge: Bilateral consent cross-agent bridges (24h TTL)
# - Memory Isolation: Copy-on-share, pull not push
# - MCP Smartness Integration: Inter-agent notifications
#
# v5.2: Batch operations, proactive compression
# v5.1: Full Context Continuity
# - Session State tracking (files_modified, tool_history, pending_tasks)
# - User Profile (role, preferences, context_rules)
# - 5-Layer Injection (Session → Pins → Threads → Profile)
#
# Supports: English (en), French (fr), Spanish (es)
# Usage: ./install.sh [project_path] [--lang=en|fr|es]
#

set -e

# Get absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
LANG_ARG=""
TARGET_DIR=""
for arg in "$@"; do
    case $arg in
        --lang=*)
            LANG_ARG="${arg#*=}"
            ;;
        -*)
            # Skip unknown flags
            ;;
        *)
            if [ -z "$TARGET_DIR" ]; then
                TARGET_DIR="$arg"
            fi
            ;;
    esac
done

# Default to current directory
TARGET_DIR="${TARGET_DIR:-.}"

# ============================================================================
# LANGUAGE SELECTION
# ============================================================================

if [ -n "$LANG_ARG" ]; then
    LANG="$LANG_ARG"
elif [ -n "$AI_SMARTNESS_LANG" ]; then
    LANG="$AI_SMARTNESS_LANG"
else
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║     Choose your language / Choisissez votre langue       ║"
    echo "║              Seleccione su idioma                        ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "  [1] English"
    echo "  [2] Français"
    echo "  [3] Español"
    echo ""
    read -p "  > " -n 1 -r LANG_CHOICE
    echo ""

    case "$LANG_CHOICE" in
        1|e|E) LANG="en" ;;
        2|f|F) LANG="fr" ;;
        3|s|S) LANG="es" ;;
        *)     LANG="en" ;;
    esac
fi

# Validate language
if [[ ! "$LANG" =~ ^(en|fr|es)$ ]]; then
    LANG="en"
fi

export AI_SMARTNESS_LANG="$LANG"

# Localized messages
declare -A MSG_BANNER_TITLE=(
    ["en"]="AI Smartness v6.2.1"
    ["fr"]="AI Smartness v6.2.1"
    ["es"]="AI Smartness v6.2.1"
)
declare -A MSG_BANNER_SUB=(
    ["en"]="Persistent Memory for Claude Agents"
    ["fr"]="Mémoire Persistante pour Agents Claude"
    ["es"]="Memoria Persistente para Agentes Claude"
)
declare -A MSG_MODE_TITLE=(
    ["en"]="Select Guardian Mode"
    ["fr"]="Sélectionnez le Mode Guardian"
    ["es"]="Seleccione el Modo Guardian"
)
declare -A MSG_MODE_HEAVY=(
    ["en"]="Deep analysis (100 threads)"
    ["fr"]="Analyse profonde (100 threads)"
    ["es"]="Análisis profundo (100 threads)"
)
declare -A MSG_MODE_NORMAL=(
    ["en"]="Balanced (50 threads)"
    ["fr"]="Équilibré (50 threads)"
    ["es"]="Equilibrado (50 threads)"
)
declare -A MSG_MODE_LIGHT=(
    ["en"]="Fast & light (15 threads)"
    ["fr"]="Rapide & léger (15 threads)"
    ["es"]="Rápido & ligero (15 threads)"
)
declare -A MSG_MODE_MAX=(
    ["en"]="Maximum memory (200 threads)"
    ["fr"]="Mémoire maximale (200 threads)"
    ["es"]="Memoria máxima (200 threads)"
)
declare -A MSG_CHOICE=(
    ["en"]="Choice [1-4]: "
    ["fr"]="Choix [1-4]: "
    ["es"]="Elección [1-4]: "
)
declare -A MSG_COPYING=(
    ["en"]="Copying files..."
    ["fr"]="Copie des fichiers..."
    ["es"]="Copiando archivos..."
)
declare -A MSG_CONFIG=(
    ["en"]="Configuring..."
    ["fr"]="Configuration..."
    ["es"]="Configurando..."
)
declare -A MSG_HOOKS=(
    ["en"]="Setting up Claude Code hooks..."
    ["fr"]="Configuration des hooks Claude Code..."
    ["es"]="Configurando hooks de Claude Code..."
)
declare -A MSG_COMPLETE=(
    ["en"]="Installation complete!"
    ["fr"]="Installation terminée!"
    ["es"]="Instalación completa!"
)
declare -A MSG_ALREADY_INSTALLED=(
    ["en"]="Already installed. Reinstall?"
    ["fr"]="Déjà installé. Réinstaller?"
    ["es"]="Ya instalado. ¿Reinstalar?"
)
declare -A MSG_KEEP_DB=(
    ["en"]="(K)eep data / (R)eset: "
    ["fr"]="(C)onserver / (R)éinitialiser: "
    ["es"]="(C)onservar / (R)einiciar: "
)
declare -A MSG_CONTINUE=(
    ["en"]="(Y)es, reinstall / (N)o, cancel: "
    ["fr"]="(O)ui, réinstaller / (N)on, annuler: "
    ["es"]="(S)í, reinstalar / (N)o, cancelar: "
)
declare -A MSG_DAEMON_START=(
    ["en"]="Starting daemon..."
    ["fr"]="Démarrage du daemon..."
    ["es"]="Iniciando daemon..."
)
declare -A MSG_DAEMON_STOP=(
    ["en"]="Stopping existing daemon"
    ["fr"]="Arrêt du daemon existant"
    ["es"]="Deteniendo daemon existente"
)
declare -A MSG_DAEMON_OK=(
    ["en"]="Daemon started"
    ["fr"]="Daemon démarré"
    ["es"]="Daemon iniciado"
)
declare -A MSG_DAEMON_MANUAL=(
    ["en"]="Daemon failed to start"
    ["fr"]="Le daemon n'a pas démarré correctement"
    ["es"]="El daemon no se inició correctamente"
)
declare -A MSG_DAEMON_HELP=(
    ["en"]="Manual start command:"
    ["fr"]="Commande de démarrage manuel:"
    ["es"]="Comando de inicio manual:"
)

# ============================================================================
# MODE SELECTION
# ============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         ${MSG_MODE_TITLE[$LANG]}                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  [1] MAX    - ${MSG_MODE_MAX[$LANG]}"
echo "  [2] Heavy  - ${MSG_MODE_HEAVY[$LANG]}"
echo "  [3] Normal - ${MSG_MODE_NORMAL[$LANG]}"
echo "  [4] Light  - ${MSG_MODE_LIGHT[$LANG]}"
echo ""
read -p "  ${MSG_CHOICE[$LANG]}" -n 1 -r MODE_CHOICE
echo ""

case "$MODE_CHOICE" in
    1|m|M) THREAD_MODE="max" ;;
    2|h|H) THREAD_MODE="heavy" ;;
    3|n|N) THREAD_MODE="normal" ;;
    4|l|L) THREAD_MODE="light" ;;
    *)     THREAD_MODE="normal" ;;
esac

echo "  ✓ Mode: $THREAD_MODE"

# ============================================================================
# BANNER
# ============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ${MSG_BANNER_TITLE[$LANG]}                         ║"
echo "║       ${MSG_BANNER_SUB[$LANG]}         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# VALIDATE TARGET
# ============================================================================

if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ Directory not found: $TARGET_DIR"
    exit 1
fi

# Convert to absolute path
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
echo "📁 Target: $TARGET_DIR"

# ============================================================================
# CHECK EXISTING INSTALLATION (v2 migration + update)
# ============================================================================

KEEP_DATA="no"
BACKUP_DIR=""
AI_SMARTNESS_DIR="$TARGET_DIR/ai_smartness"
LEGACY_DIR="$TARGET_DIR/ai_smartness_v2"

# Check for legacy v2 installation first
if [ -d "$LEGACY_DIR" ]; then
    echo ""
    echo "🔄 Found legacy ai_smartness_v2 installation - migrating to ai_smartness..."

    # Check for data in legacy installation
    LEGACY_DB="$LEGACY_DIR/.ai/db"
    if [ -d "$LEGACY_DB" ]; then
        THREAD_COUNT=$(find "$LEGACY_DB/threads" -name "*.json" 2>/dev/null | wc -l)
        BRIDGE_COUNT=$(find "$LEGACY_DB/bridges" -name "*.json" 2>/dev/null | wc -l)

        if [ "$THREAD_COUNT" -gt 0 ] || [ "$BRIDGE_COUNT" -gt 0 ]; then
            echo "   📊 Legacy data found: Threads: $THREAD_COUNT, Bridges: $BRIDGE_COUNT"
            read -p "   ${MSG_KEEP_DB[$LANG]}" -n 1 -r
            echo
            if [[ $REPLY =~ ^[KkCcGg]$ ]]; then
                KEEP_DATA="yes"
                # Backup legacy data
                BACKUP_DIR="/tmp/ai_smartness_migration_$$"
                cp -r "$LEGACY_DIR/.ai" "$BACKUP_DIR"
                echo "   ✓ Legacy data backed up for migration"
            else
                echo "   ✓ Legacy data will be reset"
            fi
        fi
    fi

    # Ask for confirmation before migration
    read -p "   ${MSG_CONTINUE[$LANG]}" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[YyOoSs]$ ]]; then
        echo "Cancelled."
        exit 0
    fi

    # Remove legacy installation
    rm -rf "$LEGACY_DIR"
    echo "   ✓ Legacy ai_smartness_v2 removed"

    # Also remove legacy entry from .claude/settings.json hooks
    CLAUDE_SETTINGS="$TARGET_DIR/.claude/settings.json"
    if [ -f "$CLAUDE_SETTINGS" ]; then
        # Replace ai_smartness_v2 with ai_smartness in hooks
        sed -i 's/ai_smartness_v2/ai_smartness/g' "$CLAUDE_SETTINGS" 2>/dev/null || true
        echo "   ✓ Updated .claude/settings.json hooks paths"
    fi
fi

# Check for current installation
if [ -d "$AI_SMARTNESS_DIR" ]; then
    echo ""
    echo "⚠️  ${MSG_ALREADY_INSTALLED[$LANG]}"

    # Check for existing data (if not already from legacy)
    if [ "$KEEP_DATA" != "yes" ]; then
        DB_DIR="$AI_SMARTNESS_DIR/.ai/db"
        if [ -d "$DB_DIR" ]; then
            THREAD_COUNT=$(find "$DB_DIR/threads" -name "*.json" 2>/dev/null | wc -l)
            BRIDGE_COUNT=$(find "$DB_DIR/bridges" -name "*.json" 2>/dev/null | wc -l)

            if [ "$THREAD_COUNT" -gt 0 ] || [ "$BRIDGE_COUNT" -gt 0 ]; then
                echo "   📊 Threads: $THREAD_COUNT, Bridges: $BRIDGE_COUNT"
                read -p "   ${MSG_KEEP_DB[$LANG]}" -n 1 -r
                echo
                if [[ $REPLY =~ ^[KkCcGg]$ ]]; then
                    KEEP_DATA="yes"
                    echo "   ✓ Data will be preserved"
                fi
            fi
        fi
    fi

    read -p "   ${MSG_CONTINUE[$LANG]}" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[YyOoSs]$ ]]; then
        echo "Cancelled."
        exit 0
    fi

    # Backup if keeping data (and not already backed up from legacy)
    if [ "$KEEP_DATA" = "yes" ] && [ -z "$BACKUP_DIR" ]; then
        DB_DIR="$AI_SMARTNESS_DIR/.ai/db"
        if [ -d "$DB_DIR" ]; then
            BACKUP_DIR="/tmp/ai_smartness_backup_$$"
            cp -r "$AI_SMARTNESS_DIR/.ai" "$BACKUP_DIR"
        fi
    fi

    rm -rf "$AI_SMARTNESS_DIR"
fi

# ============================================================================
# COPY FILES
# ============================================================================

echo ""
echo "📦 ${MSG_COPYING[$LANG]}"
cp -r "$SCRIPT_DIR" "$AI_SMARTNESS_DIR"

# Clean dev files
rm -rf "$AI_SMARTNESS_DIR/.git" 2>/dev/null || true
rm -f "$AI_SMARTNESS_DIR/.gitignore" 2>/dev/null || true
rm -rf "$AI_SMARTNESS_DIR/__pycache__" 2>/dev/null || true
find "$AI_SMARTNESS_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$AI_SMARTNESS_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove existing .ai (will restore from backup or create fresh)
rm -rf "$AI_SMARTNESS_DIR/.ai" 2>/dev/null || true

# ============================================================================
# INITIALIZE DATABASE
# ============================================================================

echo "🗄️  Initializing database..."

# Restore backup or create fresh
if [ "$KEEP_DATA" = "yes" ] && [ -d "$BACKUP_DIR" ]; then
    cp -r "$BACKUP_DIR" "$AI_SMARTNESS_DIR/.ai"
    rm -rf "$BACKUP_DIR"
    echo "   ✓ Data restored"
else
    mkdir -p "$AI_SMARTNESS_DIR/.ai/db/threads"
    mkdir -p "$AI_SMARTNESS_DIR/.ai/db/bridges"
    mkdir -p "$AI_SMARTNESS_DIR/.ai/db/synthesis"
    # v6.0 Shared Cognition directories
    mkdir -p "$AI_SMARTNESS_DIR/.ai/db/shared/published"
    mkdir -p "$AI_SMARTNESS_DIR/.ai/db/shared/subscriptions"
    mkdir -p "$AI_SMARTNESS_DIR/.ai/db/shared/cross_bridges"
    mkdir -p "$AI_SMARTNESS_DIR/.ai/db/shared/proposals/outgoing"
    mkdir -p "$AI_SMARTNESS_DIR/.ai/db/shared/proposals/incoming"
fi

# Initialize heartbeat (v4.0)
HEARTBEAT_FILE="$AI_SMARTNESS_DIR/.ai/heartbeat.json"
if [ ! -f "$HEARTBEAT_FILE" ]; then
    python3 << HBEOF
import json
from datetime import datetime

heartbeat = {
    "beat": 0,
    "started_at": datetime.now().isoformat(),
    "last_beat_at": datetime.now().isoformat(),
    "last_interaction_at": datetime.now().isoformat(),
    "last_interaction_beat": 0
}

with open("$HEARTBEAT_FILE", "w") as f:
    json.dump(heartbeat, f, indent=2)
print("   ✓ Heartbeat initialized")
HBEOF
else
    echo "   ✓ Heartbeat preserved"
fi

# ============================================================================
# INSTALL MCP PACKAGE
# ============================================================================

echo "🔌 Checking MCP package..."

if python3 -c "import mcp" 2>/dev/null; then
    echo "   ✓ mcp already installed"
else
    echo "   📦 Installing mcp (required for AI Smartness tools)..."
    if pip3 install --user mcp --quiet 2>/dev/null; then
        echo "   ✓ mcp installed successfully"
    elif pip install --user mcp --quiet 2>/dev/null; then
        echo "   ✓ mcp installed successfully"
    else
        echo "   ⚠️  Could not install mcp automatically"
        echo "   Please install manually: pip install mcp"
    fi
fi

# ============================================================================
# INSTALL SENTENCE-TRANSFORMERS
# ============================================================================

echo "🧠 Checking sentence-transformers..."

# Check if sentence-transformers is installed
if python3 -c "import sentence_transformers" 2>/dev/null; then
    echo "   ✓ sentence-transformers already installed"
else
    echo "   📦 Installing sentence-transformers (required for semantic memory)..."
    echo "   This may take a few minutes on first install..."

    if pip3 install --user sentence-transformers --quiet 2>/dev/null; then
        echo "   ✓ sentence-transformers installed successfully"
    elif pip install --user sentence-transformers --quiet 2>/dev/null; then
        echo "   ✓ sentence-transformers installed successfully"
    else
        echo "   ⚠️  Could not install sentence-transformers automatically"
        echo "   Please install manually: pip install sentence-transformers"
        echo "   (AI Smartness will use TF-IDF fallback until installed)"
    fi
fi

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

# ============================================================================
# CONFIGURE
# ============================================================================

echo "⚙️  ${MSG_CONFIG[$LANG]}"

PROJECT_NAME=$(basename "$TARGET_DIR")
CONFIG_FILE="$AI_SMARTNESS_DIR/.ai/config.json"

# IMPORTANT: Store ABSOLUTE path for hooks
AI_SMARTNESS_PATH="$AI_SMARTNESS_DIR"

python3 << EOF
import json
from pathlib import Path
from datetime import datetime

config_path = Path("$CONFIG_FILE")
thread_mode = "$THREAD_MODE"
lang = "$LANG"
project_name = "$PROJECT_NAME"
claude_cli_path = "$CLAUDE_CLI_PATH"

# Use Haiku for extraction/guardian tasks (cost-effective)
# These are lightweight LLM tasks that don't need expensive models
extraction_model = "haiku"  # Fast & cheap for title/summary extraction
guardian_model = "haiku"  # Fast & cheap for guardcode checks

# Thread limits by mode
thread_limits = {
    "max": 200,
    "heavy": 100,
    "normal": 50,
    "light": 15
}
active_threads_limit = thread_limits.get(thread_mode, 50)

config = {
    "version": "6.2.1",
    "project_name": project_name,
    "language": lang,
    "initialized_at": datetime.now().isoformat(),
    "settings": {
        "thread_mode": thread_mode,
        "auto_capture": True,
        "active_threads_limit": active_threads_limit,
        "auto_optimization": {
            "proactive_compact_enabled": True,
            "proactive_compact_threshold": 0.80,
            "auto_merge_enabled": False,
            "auto_merge_threshold": 0.90,
            "dedup_enabled": False,
            "dedup_threshold": 0.85,
            "weight_decay_enabled": False,
            "weight_decay_rate": 0.02,
            "weight_decay_min": 0.1
        },
        "shared_cognition": {
            "enabled": True,
            "auto_notify_mcp_smartness": True,
            "bridge_proposal_ttl_hours": 24,
            "default_visibility": "network"
        }
    },
    "llm": {
        "extraction_model": extraction_model,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "guardian_model": guardian_model,
        "claude_cli_path": claude_cli_path if claude_cli_path else None
    },
    "guardcode": {
        "enforce_plan_mode": True,
        "warn_quick_solutions": True,
        "require_all_choices": True
    }
}

config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
print(f"   ✓ Config saved ({thread_mode} mode, extraction: {extraction_model})")
if claude_cli_path:
    print(f"   ✓ Claude CLI: {claude_cli_path}")
EOF

# ============================================================================
# CONFIGURE CLAUDE CODE HOOKS
# ============================================================================

echo "🔧 ${MSG_HOOKS[$LANG]}"

CLAUDE_DIR="$TARGET_DIR/.claude"
mkdir -p "$CLAUDE_DIR"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

# Generate settings.json with ABSOLUTE PATHS
python3 << EOF
import json
from pathlib import Path

settings_path = Path("$SETTINGS_FILE")
# CRITICAL: Use absolute path for hooks
ai_path = "$AI_SMARTNESS_PATH"

# Load existing settings or create new
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text())
    except:
        settings = {}
else:
    settings = {}

# Permissions
if 'permissions' not in settings:
    settings['permissions'] = {'allow': []}
if 'allow' not in settings['permissions']:
    settings['permissions']['allow'] = []

if "Bash(python3:*)" not in settings['permissions']['allow']:
    settings['permissions']['allow'].append("Bash(python3:*)")

# v4 Hooks
# 4 hooks: capture (PostToolUse), inject (UserPromptSubmit), pretool (PreToolUse), compact (PreCompact)
ai_hooks = {
    "PreToolUse": [
        {
            "matcher": "Read",
            "hooks": [
                {
                    "type": "command",
                    "command": f"python3 {ai_path}/hooks/pretool.py"
                }
            ]
        }
    ],
    "UserPromptSubmit": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": f"python3 {ai_path}/hooks/inject.py"
                }
            ]
        }
    ],
    "PostToolUse": [
        {
            "matcher": "*",
            "hooks": [
                {
                    "type": "command",
                    "command": f"python3 {ai_path}/hooks/capture.py"
                }
            ]
        }
    ],
    "PreCompact": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": f"python3 {ai_path}/hooks/compact.py"
                }
            ]
        }
    ]
}

# Remove old ai_smartness hooks if present
if 'hooks' in settings:
    for hook_type in settings['hooks']:
        for hook_group in settings['hooks'][hook_type]:
            if 'hooks' in hook_group:
                hook_group['hooks'] = [
                    h for h in hook_group['hooks']
                    if 'ai_smartness' not in h.get('command', '')
                ]
        settings['hooks'][hook_type] = [
            hg for hg in settings['hooks'][hook_type]
            if hg.get('hooks')
        ]

# Add v2 hooks
if 'hooks' not in settings:
    settings['hooks'] = {}

for hook_type, hook_list in ai_hooks.items():
    if hook_type not in settings['hooks']:
        settings['hooks'][hook_type] = []
    settings['hooks'][hook_type].extend(hook_list)

# Remove mcpServers from settings.json if present (moved to .mcp.json)
if 'mcpServers' in settings:
    del settings['mcpServers']

settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False))
print("   ✓ Hooks configured (PreToolUse, UserPromptSubmit, PostToolUse, PreCompact)")
print(f"   ✓ Using absolute path: {ai_path}")
EOF

# ============================================================================
# CONFIGURE MCP SERVER (.mcp.json)
# ============================================================================

echo "🔌 Configuring MCP server..."

MCP_CONFIG_FILE="$TARGET_DIR/.mcp.json"

python3 << EOF
import json
from pathlib import Path

mcp_path = Path("$MCP_CONFIG_FILE")
ai_path = "$AI_SMARTNESS_PATH"

# Load existing config or create new
if mcp_path.exists():
    try:
        mcp_config = json.loads(mcp_path.read_text())
    except:
        mcp_config = {}
else:
    mcp_config = {}

if 'mcpServers' not in mcp_config:
    mcp_config['mcpServers'] = {}

# Add/update ai-smartness MCP server
mcp_config['mcpServers']['ai-smartness'] = {
    "type": "stdio",
    "command": "python3",
    "args": [f"{ai_path}/mcp/server.py"],
    "env": {
        "PYTHONPATH": str(Path(ai_path).parent)
    }
}

mcp_path.write_text(json.dumps(mcp_config, indent=2, ensure_ascii=False))
print("   ✓ MCP server configured in .mcp.json")
print(f"   ✓ Server path: {ai_path}/mcp/server.py")
EOF

# ============================================================================
# CONFIGURE .gitignore
# ============================================================================

echo "📝 Configuring .gitignore..."
GITIGNORE="$TARGET_DIR/.gitignore"

GITIGNORE_ENTRIES="
# AI Smartness
ai_smartness/
.mcp.json
"

if [ -f "$GITIGNORE" ]; then
    if ! grep -q "^ai_smartness/$" "$GITIGNORE" 2>/dev/null; then
        echo "$GITIGNORE_ENTRIES" >> "$GITIGNORE"
        echo "   ✓ Entries added"
    else
        echo "   ✓ Already configured"
    fi
else
    echo "$GITIGNORE_ENTRIES" > "$GITIGNORE"
    echo "   ✓ Created"
fi

# ============================================================================
# CONFIGURE .claudeignore
# ============================================================================

CLAUDEIGNORE="$TARGET_DIR/.claudeignore"
CLAUDEIGNORE_ENTRIES="# AI Smartness - invisible to agent
ai_smartness/
.claude/"

if [ -f "$CLAUDEIGNORE" ]; then
    if ! grep -q "^ai_smartness/$" "$CLAUDEIGNORE" 2>/dev/null; then
        echo "" >> "$CLAUDEIGNORE"
        echo "$CLAUDEIGNORE_ENTRIES" >> "$CLAUDEIGNORE"
    fi
else
    echo "$CLAUDEIGNORE_ENTRIES" > "$CLAUDEIGNORE"
fi
echo "   ✓ .claudeignore configured"

# ============================================================================
# INSTALL CLI
# ============================================================================

echo "🖥️  Installing CLI..."

# Create bin directory if needed
mkdir -p "$AI_SMARTNESS_DIR/bin"

# Create the ai wrapper script
cat > "$AI_SMARTNESS_DIR/bin/ai" << 'AIEOF'
#!/bin/bash
#
# AI Smartness CLI
#

# Find the ai_smartness directory
find_ai_smartness() {
    local dir="$PWD"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/ai_smartness" ]; then
            echo "$dir/ai_smartness"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

AI_SMARTNESS_PATH=$(find_ai_smartness)

if [ -z "$AI_SMARTNESS_PATH" ]; then
    echo "Error: Could not find ai_smartness directory"
    exit 1
fi

# Add parent to PYTHONPATH for imports
export PYTHONPATH="${AI_SMARTNESS_PATH%/*}:$PYTHONPATH"

exec python3 "$AI_SMARTNESS_PATH/cli/main.py" "$@"
AIEOF

chmod +x "$AI_SMARTNESS_DIR/bin/ai"

# Install to ~/.local/bin if available
LOCAL_BIN="$HOME/.local/bin"
if [ -d "$LOCAL_BIN" ]; then
    cp "$AI_SMARTNESS_DIR/bin/ai" "$LOCAL_BIN/ai"
    chmod +x "$LOCAL_BIN/ai"
    echo "   ✓ CLI installed to $LOCAL_BIN/ai"

    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        echo "   ⚠️  Add $LOCAL_BIN to your PATH:"
        echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
else
    mkdir -p "$LOCAL_BIN"
    cp "$AI_SMARTNESS_DIR/bin/ai" "$LOCAL_BIN/ai"
    chmod +x "$LOCAL_BIN/ai"
    echo "   ✓ CLI installed to $LOCAL_BIN/ai"
    echo "   ⚠️  Add $LOCAL_BIN to your PATH:"
    echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# ============================================================================
# START/RESTART DAEMON
# ============================================================================

echo "🚀 ${MSG_DAEMON_START[$LANG]}"

PID_FILE="$AI_SMARTNESS_DIR/.ai/processor.pid"
SOCKET_FILE="$AI_SMARTNESS_DIR/.ai/processor.sock"

# Kill ALL existing daemons for this project (including zombies)
echo "   Cleaning up existing daemons..."
pkill -9 -f "ai_smartness.daemon.processor.*$TARGET_DIR" 2>/dev/null || true
pkill -9 -f "ai_smartness/daemon/processor.py.*$AI_SMARTNESS_DIR" 2>/dev/null || true

# Also kill by PID file if exists
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ]; then
        kill -9 "$OLD_PID" 2>/dev/null || true
    fi
fi

# Clean up stale files
rm -f "$PID_FILE" 2>/dev/null
rm -f "$SOCKET_FILE" 2>/dev/null
sleep 1

# Start the daemon
export PYTHONPATH="$TARGET_DIR:$PYTHONPATH"
python3 -c "
import sys
sys.path.insert(0, '$TARGET_DIR')
from ai_smartness.daemon.client import ensure_daemon_running
from pathlib import Path
ai_path = Path('$AI_SMARTNESS_DIR/.ai')
ensure_daemon_running(ai_path)
" 2>/dev/null

# Wait for daemon to start (polling up to 10 seconds)
DAEMON_STARTED=false
for i in {1..10}; do
    if [ -f "$PID_FILE" ]; then
        NEW_PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$NEW_PID" ] && kill -0 "$NEW_PID" 2>/dev/null; then
            DAEMON_STARTED=true
            break
        fi
    fi
    sleep 1
done

if [ "$DAEMON_STARTED" = true ]; then
    echo "   ✓ ${MSG_DAEMON_OK[$LANG]} (PID $NEW_PID)"
else
    echo "   ❌ ${MSG_DAEMON_MANUAL[$LANG]}"
    echo ""
    echo "   ⚠️  ${MSG_DAEMON_HELP[$LANG]}"
    echo "      cd $TARGET_DIR && python3 -m ai_smartness.daemon.processor --db-path $AI_SMARTNESS_DIR/.ai/db"
fi

# ============================================================================
# COMPLETE
# ============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ${MSG_COMPLETE[$LANG]}                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📍 Installed in: $AI_SMARTNESS_DIR"
echo ""
echo "🔧 Configuration:"
echo "   • Hooks: $CLAUDE_DIR/settings.json"
echo "   • MCP: $TARGET_DIR/.mcp.json"
echo "   • Database: $AI_SMARTNESS_DIR/.ai/db/"
echo "   • Config: $AI_SMARTNESS_DIR/.ai/config.json"
echo ""
echo "📋 Features:"
echo "   • Thread-based memory (Neurons)"
echo "   • ThinkBridges (Synapses)"
echo "   • Gossip propagation"
echo "   • GuardCode enforcement"
echo "   • 95% context synthesis"
echo "   • Recall Actif (v4.0)"
echo "   • Heartbeat temporal awareness (v4.1)"
echo "   • V5 Hybrid: Focus boost, relevance scoring, proactive suggestions"
echo "   • V5.1 Full Context Continuity: Session state, user profile, layered injection"
echo "   • V5.2 Auto-Optimization: Batch operations, proactive compression"
echo "   • V6.0 Shared Cognition: Inter-agent memory sharing with isolation"
echo "   • V6.1 Bridge Management: ai_bridges, ai_bridge_analysis"
echo "   • V6.2 Phase 3: ai_recommend, ai_topics, shared context injection, bridge strength"
echo ""
echo "🖥️  CLI Commands:"
echo "   ai status      - Show memory status"
echo "   ai threads     - List threads"
echo "   ai thread <id> - Show thread details"
echo "   ai bridges     - List bridges"
echo "   ai search <q>  - Search threads"
echo "   ai recall <q>  - Search memory (incl. suspended)"
echo "   ai heartbeat   - Show heartbeat status"
echo "   ai reindex     - Recalculate embeddings"
echo "   ai health      - System health check"
echo "   ai daemon      - Daemon control (start/stop/status)"
echo "   ai mode        - View/change mode (light/normal/heavy/max)"
echo "   ai help        - Show help"
echo ""
echo "🔧 MCP Tools (v6.2):"
echo "   ai_recall(query)     - Semantic memory search"
echo "   ai_merge(s, a)       - Merge threads"
echo "   ai_split(id)         - Split thread"
echo "   ai_unlock(id)        - Unlock thread"
echo "   ai_help()            - Documentation"
echo "   ai_status()          - Memory status"
echo ""
echo "🆕 V5 Hybrid Tools:"
echo "   ai_suggestions()     - Proactive memory optimization"
echo "   ai_compact(strategy) - On-demand compaction (gentle/normal/aggressive)"
echo "   ai_focus(topics)     - Boost injection priority for topics"
echo "   ai_unfocus()         - Clear focus topics"
echo "   ai_pin(content)      - High-priority content capture"
echo "   ai_rate_context(id,useful) - Feedback on injection quality"
echo ""
echo "🔄 V5.1 Context Continuity:"
echo "   ai_profile(action)   - User profile management (role, preferences, rules)"
echo "   Session State        - Automatic work context tracking"
echo "   Layered Injection    - 5-layer priority context system"
echo ""
echo "📦 V5.2 Batch & Auto-Optimization:"
echo "   ai_merge_batch(ops)  - Merge multiple threads at once"
echo "   ai_rename_batch(ops) - Rename multiple threads at once"
echo "   ai_cleanup(mode)     - Fix threads with bad titles"
echo "   ai_rename(id,title)  - Rename a single thread"
echo "   Proactive Compression - Auto-compact when pressure > 0.80"
echo ""
echo "🌐 V6.0 Shared Cognition (Inter-Agent Memory):"
echo "   ai_share(thread_id)  - Share a thread to the network"
echo "   ai_unshare(shared_id) - Remove shared thread"
echo "   ai_publish(shared_id) - Publish update to subscribers"
echo "   ai_discover(topics)  - Find shared threads by topics"
echo "   ai_subscribe(id)     - Subscribe to a shared thread"
echo "   ai_unsubscribe(id)   - Unsubscribe from shared thread"
echo "   ai_sync()            - Sync all stale subscriptions"
echo "   ai_shared_status()   - Show shared cognition status"
echo ""
echo "🔗 V6.0 Inter-Agent Bridges (requires bilateral consent):"
echo "   ai_propose_bridge()  - Propose a cross-agent bridge"
echo "   ai_accept_bridge()   - Accept incoming proposal"
echo "   ai_reject_bridge()   - Reject incoming proposal"
echo "   Proposals expire after 24 hours if not accepted"
echo ""
echo "🔗 V6.1 Bridge Management Suite:"
echo "   ai_bridges(thread_id?, relation_type?, status?) - List/filter bridges"
echo "   ai_bridge_analysis()  - Bridge network analytics (stats, health, distribution)"
echo ""
echo "🚀 V6.2 Phase 3 - Advanced Shared Cognition:"
echo "   ai_recommend(limit?)  - Subscription recommendations based on topic overlap"
echo "   ai_topics(agent_id?)  - Network-wide topic discovery & cross-agent overlap"
echo "   Shared Context Injection - Subscribed threads auto-injected in recall context"
echo "   Bridge Strength        - Cross-agent usage tracking for dynamic weight"
echo ""
echo "✨ Ready to use! Start a new Claude Code session."
echo ""
