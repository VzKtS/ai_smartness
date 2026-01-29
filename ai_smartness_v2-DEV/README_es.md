# AI Smartness v2

**Capa de meta-cognición para agentes Claude Code.**

Un sistema de memoria persistente que transforma Claude Code en un agente capaz de mantener contexto semántico a través de sesiones largas, detectar conexiones entre conceptos, y retomar el trabajo después de semanas/meses como si solo hubieras ido a tomar un café.

Compatible con VS Code & Claude Code CLI.

---

## Visión

AI Smartness v2 es una **memoria de trabajo inspirada en redes neuronales**:

- **Threads** = Neuronas (flujos de razonamiento activos)
- **ThinkBridges** = Sinapsis (conexiones semánticas entre threads)
- **Gossip** = Propagación de señal a través de la red
- **Inyección de Memoria** = Restauración del contexto en cada prompt

El sistema mantiene una **red de pensamientos** donde los conceptos permanecen conectados y accesibles, evitando la pérdida de contexto típica de las interacciones LLM clásicas.

---

## Características Principales

| Característica | Descripción |
|----------------|-------------|
| **Threads** | Unidades de trabajo semánticas con títulos auto-generados |
| **ThinkBridges** | Conexiones automáticas entre threads relacionados |
| **Propagación Gossip** | Los bridges se propagan cuando los conceptos evolucionan |
| **Inyección de Memoria** | Contexto relevante inyectado en cada prompt |
| **Reglas de Usuario** | Detección y persistencia automática de tus preferencias |
| **GuardCode** | Aplicación del modo plan, protección contra deriva |
| **Síntesis 95%** | Preservación automática del contexto antes del compactado |
| **Arquitectura Daemon** | Procesamiento en segundo plano para respuesta rápida |
| **100% Transparente** | Cero acción del usuario requerida |

---

## Instalación

```bash
# Clona o copia ai_smartness_v2-DEV en tu máquina
# Luego ejecuta la instalación en tu proyecto destino:
/ruta/a/ai_smartness_v2-DEV/install.sh /ruta/a/tu/proyecto
```

### Qué hace el instalador

1. **Selección de idioma**: Inglés, Francés o Español
2. **Selección de modo**: Heavy, Normal o Light (afecta límites de threads)
3. **Instala sentence-transformers** (si no está instalado)
4. **Detecta el CLI Claude** para extracción LLM
5. **Copia los archivos** a `tu_proyecto/ai_smartness_v2/`
6. **Configura los hooks** con rutas absolutas en `.claude/settings.json`
7. **Inicializa la base de datos** en `ai_smartness_v2/.ai/db/`
8. **Instala el CLI** en `~/.local/bin/ai`

### Requisitos

- Python 3.10+
- Claude Code (CLI o extensión VS Code)
- pip (para instalación automática de sentence-transformers)

El instalador gestiona las dependencias automáticamente. Si sentence-transformers falla, el sistema usa TF-IDF (funcional pero menos preciso).

---

## Comandos CLI

Después de la instalación, usa el comando `ai` desde tu directorio del proyecto:

```bash
# Vista general
ai status

# Listar threads
ai threads
ai threads --status active
ai threads --status suspended
ai threads --limit 20

# Ver thread específico
ai thread <thread_id>

# Listar bridges
ai bridges
ai bridges --thread <thread_id>

# Búsqueda semántica
ai search "autenticación"

# Verificación de salud
ai health

# Recalcular embeddings
ai reindex

# Control del daemon
ai daemon           # Mostrar estado
ai daemon status    # Mostrar estado
ai daemon start     # Iniciar daemon
ai daemon stop      # Detener daemon
```

---

## Cómo Funciona

### 1. Captura (hook PostToolUse)

Cada resultado de herramienta (Read, Write, Task, etc.) se envía al daemon:
```
[Resultado Herramienta] → [Daemon] → [Filtro Ruido] → [Extracción LLM] → [Decisión Thread]
```

### 2. Gestión de Threads

El sistema decide para cada entrada:
- **NEW_THREAD**: Tema diferente → crear nuevo thread
- **CONTINUE**: Mismo tema → añadir al thread activo (similitud > 0.35)
- **FORK**: Sub-tema → crear thread hijo
- **REACTIVATE**: Tema antiguo vuelve → despertar thread suspendido (similitud > 0.50)

### 3. Propagación Gossip

Cuando un thread cambia:
```
Thread A modificado → Recalcular embedding
                    → Para cada thread B conectado
                    → Si similitud alta → propagar bridges
```

### 4. Inyección de Memoria (hook UserPromptSubmit)

Antes de cada prompt del usuario, se inyecta el contexto relevante:
```xml
<system-reminder>
AI Smartness Memory Context:

Current thread: "Sistema de Autenticación"
Summary: Implementando auth JWT con refresh tokens...

Related threads:
- "Esquema Base de Datos" - Diseño tablas usuarios
- "Endpoints API" - Rutas de autenticación

User rules:
- siempre hacer un plan antes de implementar
</system-reminder>
```

El usuario no ve nada - es invisible para ti pero visible para el agente.

### 5. Detección de Reglas de Usuario

El sistema detecta y almacena automáticamente tus preferencias:
- "recuerda: siempre usar TypeScript"
- "regla: sin console.log en producción"
- "siempre hacer un plan antes de implementar"
- "nunca commit directo a main"

Las reglas se almacenan en `ai_smartness_v2/.ai/user_rules.json` y se inyectan en cada prompt.

### 6. Síntesis (hook PreCompact)

Al 95% de la ventana de contexto:
- El LLM genera una síntesis del estado actual
- Decisiones, preguntas abiertas, threads activos
- Inyectado después del compactado
- El usuario no ve nada

---

## Configuración

Config almacenada en `ai_smartness_v2/.ai/config.json`:

```json
{
  "version": "2.0.0",
  "project_name": "MiProyecto",
  "language": "es",
  "settings": {
    "thread_mode": "heavy",
    "auto_capture": true,
    "active_threads_limit": 100
  },
  "llm": {
    "extraction_model": "claude-3-5-haiku-20241022",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "claude_cli_path": "/usr/local/bin/claude"
  },
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true,
    "require_all_choices": true
  }
}
```

### Diferencias entre Modos

| Modo | Límite Threads | Caso de Uso |
|------|----------------|-------------|
| Light | 15 | Proyectos pequeños |
| Normal | 50 | Proyectos medianos |
| Heavy | 100 | Proyectos grandes y complejos |

### Umbrales de Similitud

| Contexto | Umbral | Descripción |
|----------|--------|-------------|
| Continuación thread activo | 0.35 | Mínimo para continuar un thread |
| Reactivación thread suspendido | 0.50 | Mínimo para despertar un thread |
| Boost de topic | +0.15 | Bonus por coincidencia exacta de topic |

---

## Estructura Base de Datos

```
ai_smartness_v2/.ai/
├── config.json           # Configuración
├── user_rules.json       # Reglas de usuario
├── processor.pid         # PID del daemon
├── processor.sock        # Socket del daemon
├── processor.log         # Logs del daemon
├── inject.log            # Logs de inyección
└── db/
    ├── threads/          # Archivos JSON de threads
    ├── bridges/          # Archivos JSON de bridges
    └── synthesis/        # Síntesis de compactado
```

---

## Solución de Problemas

### Daemon no iniciado

```bash
ai daemon status
# Si está detenido:
ai daemon start
```

### Capturas no funcionan

Verifica las rutas de los hooks en `.claude/settings.json` - deben ser **absolutas**.

### "Heuristic fallback" en títulos

CLI Claude no encontrado:
```bash
which claude
# Actualiza la ruta en config.json si es necesario
```

### Scores de similitud bajos / Mala memoria

sentence-transformers no instalado:
```bash
pip install sentence-transformers
ai daemon stop
ai daemon start
ai reindex
```

### Tasa de continuación baja

Verifica con `ai health`. Si < 10%:
1. Verifica que sentence-transformers esté instalado
2. Ejecuta `ai reindex`
3. Revisa `ai_smartness_v2/.ai/processor.log`

---

## Arquitectura

### Componentes

| Componente | Archivo | Rol |
|------------|---------|-----|
| Daemon | `daemon/processor.py` | Procesamiento en segundo plano |
| Client | `daemon/client.py` | Comunicación rápida con daemon |
| Hook Captura | `hooks/capture.py` | Captura PostToolUse |
| Hook Inyección | `hooks/inject.py` | Inyección UserPromptSubmit |
| Hook Compact | `hooks/compact.py` | Síntesis PreCompact |
| Memory Retriever | `intelligence/memory_retriever.py` | Recuperación de contexto |
| Thread Manager | `intelligence/thread_manager.py` | Ciclo de vida de threads |
| Gossip | `intelligence/gossip.py` | Propagación de bridges |
| Embeddings | `processing/embeddings.py` | Embeddings vectoriales |

---

## Licencia

MIT

---

**Nota**: AI Smartness v2 está diseñado para ser invisible. La mejor indicación de que funciona es que tu agente "recuerda" el contexto entre sesiones sin que hagas nada especial.
