# AI Smartness v5.1

**Capa de meta-cognición para agentes Claude Code.**

Un sistema de memoria persistente que transforma Claude Code en un agente capaz de mantener contexto semántico a través de sesiones largas, detectar conexiones entre conceptos, y retomar el trabajo después de semanas/meses como si solo hubieras ido a tomar un café.

Compatible con VS Code & Claude Code CLI.

---

## Filosofía: Asociación, no Control

AI Smartness permite una **asociación** entre tú y tu agente. Proporciona herramientas cognitivas - no restricciones.

- **GuardCode es consultivo**: Sugerencias, no imposición
- **Los primeros contactos importan**: Deja que los conceptos emerjan naturalmente con nuevos agentes
- **La confianza se desarrolla con el tiempo**: El agente aprende tus preferencias a través de la colaboración
- **Autonomía del agente**: El agente gestiona activamente su propia cognición y ventana contextual

Ver el [README principal](../../README.md) para la discusión completa sobre filosofía.

---

## Visión

AI Smartness v5.1 es una **memoria de trabajo inspirada en redes neuronales** con **continuidad contextual completa**:

- **Threads** = Neuronas (flujos de razonamiento activos)
- **ThinkBridges** = Sinapsis (conexiones semánticas entre threads)
- **Recall** = Recuperación activa de memoria bajo demanda
- **Inyección de Memoria** = Restauración del contexto en cada prompt
- **Estado de Sesión** = Continuidad del trabajo entre sesiones
- **Perfil de Usuario** = Personalización persistente

El sistema mantiene una **red de pensamientos** donde los conceptos permanecen conectados y accesibles.

---

## Características Clave v5.1

| Característica | Descripción |
|----------------|-------------|
| **Threads** | Unidades de trabajo semánticas con títulos auto-generados |
| **ThinkBridges** | Conexiones automáticas entre threads relacionados |
| **Herramientas MCP** | Herramientas nativas para gestión de memoria |
| **Merge/Split** | Topología de memoria controlada por el agente |
| **Seguimiento Contexto** | % contexto en tiempo real con throttle adaptativo |
| **Estado de Sesión** | Seguimiento de archivos, historial de herramientas, tareas |
| **Perfil de Usuario** | Rol, preferencias, reglas contextuales |
| **Inyección en Capas** | Sistema de contexto con 5 niveles de prioridad |
| **Intro Cooperativa** | El agente gestiona activamente su cognición |
| **CLI en el Prompt** | `ai status` directamente en el prompt |
| **Reglas Usuario** | Detección y persistencia automática de preferencias |
| **GuardCode** | Sistema consultivo para buenas prácticas |
| **Síntesis 95%** | Preservación automática del contexto antes de compactación |
| **100% Transparente** | Ninguna acción del usuario requerida |

---

## Herramientas MCP del Agente (v5.2)

Tu agente tiene acceso a herramientas MCP nativas:

### Herramientas Base
```
ai_recall(query="autenticacion")   # Búsqueda por palabra clave/tema
ai_help()                          # Auto-documentación del agente
ai_status()                        # Estado de memoria
```

### Gestión de Threads
```
ai_merge(survivor_id="t1", absorbed_id="t2")   # Fusionar dos threads
ai_split(thread_id="t1")                        # Info split (paso 1)
ai_split(thread_id="t1", confirm=True, ...)    # Ejecutar split (paso 2)
ai_unlock(thread_id="t1")                       # Desbloquear thread
```

### Herramientas V5 Híbridas
```
ai_suggestions()              # Sugerencias de optimización proactivas
ai_compact(strategy="normal") # Compactación bajo demanda (gentle/normal/aggressive)
ai_focus(topic="solana")      # Aumentar prioridad de inyección para temas
ai_unfocus()                  # Limpiar topics de focus
ai_pin(content="importante")  # Captura de alta prioridad
ai_rate_context(thread_id, useful=True)  # Feedback sobre calidad de inyección
```

### V5.1 Continuidad Contextual
```
ai_profile(action="view")                          # Ver perfil
ai_profile(action="set_role", role="developer")    # Definir rol
ai_profile(action="add_rule", rule="Siempre usar TypeScript")  # Agregar regla
```

### V5.2 Operaciones Batch & Auto-Optimización
```
ai_merge_batch(operations=[...])   # Fusionar múltiples threads de una vez
ai_rename_batch(operations=[...])  # Renombrar múltiples threads de una vez
ai_cleanup(mode="auto")            # Corregir threads con títulos malos
ai_cleanup(mode="interactive")     # Revisar antes de corregir
ai_rename(thread_id, new_title)    # Renombrar un thread
```
**Compresión Proactiva:** El daemon compacta auto cuando la presión > 0.80

---

## Instalación

**Plataforma:** Linux / macOS / Windows (solo vía WSL)

> Los hooks requieren rutas Unix absolutas. Las rutas nativas de Windows no son compatibles.

### Pre-requisitos (Recomendado)

**sentence-transformers** requiere PyTorch. Recomendamos la instalación **antes** del script de instalación para elegir tu variante:

```bash
# Solo CPU (más ligero)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers

# O con CUDA (más rápido con GPU NVIDIA)
pip install torch && pip install sentence-transformers
```

### Ejecutar la Instalación

```bash
/ruta/a/ai_smartness-DEV/install.sh /ruta/a/tu/proyecto
```

### Qué hace el Instalador

| Paso | Acción |
|------|--------|
| 1 | **Selección idioma** (en/fr/es) |
| 2 | **Selección modo** (MAX/Heavy/Normal/Light → límites threads) |
| 3 | **Migración** desde `ai_smartness_v2` si presente |
| 4 | **Copia archivos** a `proyecto/ai_smartness/` |
| 5 | **Inicializa base de datos** (threads, bridges, synthesis) |
| 6 | **Inicializa heartbeat.json** (seguimiento de sesión) |
| 7 | **Verifica sentence-transformers** (auto-install si ausente) |
| 8 | **Detecta Claude CLI** |
| 9 | **Crea config.json** |
| 10 | **Configura hooks** (4 hooks con rutas absolutas) |
| 11 | **Configura servidor MCP** (herramientas ai-smartness) |
| 12 | **Configura .gitignore/.claudeignore** |
| 13 | **Instala CLI** en `~/.local/bin/ai` |
| 14 | **Inicia daemon** (procesador en segundo plano) |

### El Daemon

Un daemon en segundo plano gestiona:
- Procesamiento asíncrono de capturas
- Extracción LLM para decisiones de threads
- Auto-pruning cada 5 minutos

```bash
ai daemon status/start/stop
```

### Requisitos

- Python 3.10+
- Claude Code (CLI o extensión VS Code)
- sentence-transformers (auto-instalado o pre-instalado)

---

## Comandos CLI

```bash
# Vista general
ai status

# Listar threads
ai threads
ai threads --status active
ai threads --prune

# Ver thread específico
ai thread <thread_id>

# Listar bridges
ai bridges
ai bridges --thread <thread_id>

# Búsqueda semántica
ai search "autenticación"

# Salud del sistema
ai health

# Recalcular embeddings
ai reindex

# Control daemon
ai daemon start
ai daemon stop

# Gestión modo
ai mode heavy
```

### En el Prompt (v3.0.0+)

Escribe los comandos CLI directamente:
```
Tú: ai status
Claude: [Muestra el estado de la memoria]
```

---

## Funcionamiento

### 1. Captura (hook PostToolUse)
```
[Resultado Herramienta] → [Daemon] → [Extracción LLM] → [Decisión Thread]
```

### 2. Gestión de Threads
- **NEW_THREAD**: Tema diferente
- **CONTINUE**: Mismo tema (similitud > 0.35)
- **FORK**: Sub-tema
- **REACTIVATE**: Tema antiguo vuelve (similitud > 0.50)

### 3. Recall Activo (v4.4)
```
ai_recall(query="autenticación")
→ Devuelve threads, resúmenes, bridges
```

### 4. Inyección de Memoria (UserPromptSubmit)

Nuevas sesiones reciben:
- Vista general de capabilities
- Último thread activo ("hot thread")
- Sugerencias de recall

Cada mensaje recibe:
- Threads relevantes por similitud
- Reglas de usuario

### 5. Seguimiento de Contexto (v4.3)
- <70%: Actualización cada 30s
- ≥70%: Actualización solo con delta 5%

### 6. Síntesis (PreCompact, 95%)
Síntesis de estado auto-generada antes de compactación.

---

## Configuración

```json
{
  "version": "4.3.0",
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100
  },
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true
  }
}
```

### Modos

| Modo | Límite Threads |
|------|----------------|
| Light | 15 |
| Normal | 50 |
| Heavy | 100 |
| Max | 200 |

---

## Arquitectura

### Componentes

| Componente | Archivo | Rol |
|------------|---------|-----|
| Daemon | `daemon/processor.py` | Procesamiento en segundo plano |
| Client | `daemon/client.py` | Comunicación rápida |
| Hook Captura | `hooks/capture.py` | PostToolUse |
| Hook Inyección | `hooks/inject.py` | UserPromptSubmit |
| Hook PreTool | `hooks/pretool.py` | Rutas virtuales .ai/ |
| Handler Recall | `hooks/recall.py` | Recall memoria + merge/split |
| Hook Compact | `hooks/compact.py` | Síntesis PreCompact |

### Hooks

| Hook | Script | Función |
|------|--------|---------|
| `UserPromptSubmit` | inject.py | Comandos CLI + inyección memoria |
| `PreToolUse` | pretool.py | Rutas virtuales .ai/ |
| `PostToolUse` | capture.py | Captura threads |
| `PreCompact` | compact.py | Generación síntesis |

---

## Solución de Problemas

### Daemon no iniciado
```bash
ai daemon start
```

### El agente no usa recall
Normal para nuevos agentes. Necesitan descubrir sus herramientas:
1. Menciona que `ai_recall()` existe
2. Apunta a `ai_help()`
3. Confía en el proceso de aprendizaje

### Scores de similitud bajos
```bash
pip install sentence-transformers
ai daemon stop && ai daemon start
ai reindex
```

---

## Estructura Base de Datos

```
ai_smartness/.ai/
├── config.json
├── heartbeat.json        # Seguimiento sesión, % contexto
├── user_rules.json
├── processor.pid
├── processor.sock
├── processor.log
├── inject.log
└── db/
    ├── threads/
    ├── bridges/
    └── synthesis/
```

---

## Licencia

MIT

---

**Nota**: AI Smartness está diseñado para ser invisible. La mejor indicación de que funciona es que tu agente se convierte en un mejor colaborador con el tiempo - no que nunca ocurra nada malo.
