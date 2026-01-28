#!/bin/bash
#
# AI Smartness v2 Installation Script
# Simplified architecture with absolute paths
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
    ["en"]="AI Smartness v2.0"
    ["fr"]="AI Smartness v2.0"
    ["es"]="AI Smartness v2.0"
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
    ["en"]="Deep analysis (Opus)"
    ["fr"]="Analyse profonde (Opus)"
    ["es"]="Análisis profundo (Opus)"
)
declare -A MSG_MODE_NORMAL=(
    ["en"]="Balanced (Sonnet)"
    ["fr"]="Équilibré (Sonnet)"
    ["es"]="Equilibrado (Sonnet)"
)
declare -A MSG_MODE_LIGHT=(
    ["en"]="Fast & economical (Haiku)"
    ["fr"]="Rapide & économique (Haiku)"
    ["es"]="Rápido & económico (Haiku)"
)
declare -A MSG_CHOICE=(
    ["en"]="Choice [1-3]: "
    ["fr"]="Choix [1-3]: "
    ["es"]="Elección [1-3]: "
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
    ["en"]="Keep existing data? [K/R]: "
    ["fr"]="Conserver les données? [C/R]: "
    ["es"]="¿Conservar datos? [C/R]: "
)

# ============================================================================
# MODE SELECTION
# ============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         ${MSG_MODE_TITLE[$LANG]}                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  [1] Heavy  - ${MSG_MODE_HEAVY[$LANG]}"
echo "  [2] Normal - ${MSG_MODE_NORMAL[$LANG]}"
echo "  [3] Light  - ${MSG_MODE_LIGHT[$LANG]}"
echo ""
read -p "  ${MSG_CHOICE[$LANG]}" -n 1 -r MODE_CHOICE
echo ""

case "$MODE_CHOICE" in
    1|h|H) THREAD_MODE="heavy" ;;
    2|n|N) THREAD_MODE="normal" ;;
    3|l|L) THREAD_MODE="light" ;;
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
# CHECK EXISTING INSTALLATION
# ============================================================================

KEEP_DATA="no"
AI_SMARTNESS_DIR="$TARGET_DIR/_ai_smartness_v2"

if [ -d "$AI_SMARTNESS_DIR" ]; then
    echo ""
    echo "⚠️  ${MSG_ALREADY_INSTALLED[$LANG]}"

    # Check for existing data
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

    read -p "   Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[YyOoSs]$ ]]; then
        echo "Cancelled."
        exit 0
    fi

    # Backup if keeping data
    if [ "$KEEP_DATA" = "yes" ] && [ -d "$DB_DIR" ]; then
        BACKUP_DIR="/tmp/_ai_smartness_v2_backup_$$"
        cp -r "$AI_SMARTNESS_DIR/.ai" "$BACKUP_DIR"
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

# Extraction always uses Haiku (sufficient for semantic extraction, economical)
# The mode only affects thread limits and injection depth, not extraction cost
# Note: If model becomes invalid, extractor will fallback to session default
extraction_model = "claude-3-5-haiku-20241022"
guardian_model = extraction_model  # Guardian also uses Haiku

# Thread limits by mode
thread_limits = {
    "heavy": 100,
    "normal": 50,
    "light": 15
}
active_threads_limit = thread_limits.get(thread_mode, 50)

config = {
    "version": "2.0.0",
    "project_name": project_name,
    "language": lang,
    "initialized_at": datetime.now().isoformat(),
    "settings": {
        "thread_mode": thread_mode,
        "auto_capture": True,
        "active_threads_limit": active_threads_limit
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

# v2 Hooks - SIMPLIFIED
# Only 3 hooks: capture (PostToolUse), inject (UserPromptSubmit), compact (PreCompact)
ai_hooks = {
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

settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False))
print("   ✓ Hooks configured (UserPromptSubmit, PostToolUse, PreCompact)")
print(f"   ✓ Using absolute path: {ai_path}")
EOF

# ============================================================================
# CONFIGURE .gitignore
# ============================================================================

echo "📝 Configuring .gitignore..."
GITIGNORE="$TARGET_DIR/.gitignore"

GITIGNORE_ENTRIES="
# AI Smartness v2
_ai_smartness_v2/
.ai/
"

if [ -f "$GITIGNORE" ]; then
    if ! grep -q "^_ai_smartness_v2/$" "$GITIGNORE" 2>/dev/null; then
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
CLAUDEIGNORE_ENTRIES="# AI Smartness v2 - invisible to agent
_ai_smartness_v2/
.claude/"

if [ -f "$CLAUDEIGNORE" ]; then
    if ! grep -q "^_ai_smartness_v2/$" "$CLAUDEIGNORE" 2>/dev/null; then
        echo "" >> "$CLAUDEIGNORE"
        echo "$CLAUDEIGNORE_ENTRIES" >> "$CLAUDEIGNORE"
    fi
else
    echo "$CLAUDEIGNORE_ENTRIES" > "$CLAUDEIGNORE"
fi
echo "   ✓ .claudeignore configured"

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
echo "   • Database: $AI_SMARTNESS_DIR/.ai/db/"
echo "   • Config: $AI_SMARTNESS_DIR/.ai/config.json"
echo ""
echo "📋 Features:"
echo "   • Thread-based memory (Neurons)"
echo "   • ThinkBridges (Synapses)"
echo "   • Gossip propagation"
echo "   • GuardCode enforcement"
echo "   • 95% context synthesis"
echo ""
echo "✨ Ready to use! Start a new Claude Code session."
echo ""
