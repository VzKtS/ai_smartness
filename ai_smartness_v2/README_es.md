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

El sistema mantiene una **red de pensamientos** donde los conceptos permanecen conectados y accesibles, evitando la pérdida de contexto típica de las interacciones LLM clásicas.

---

## Características Principales

| Característica | Descripción |
|----------------|-------------|
| **Threads** | Unidades de trabajo semánticas con títulos auto-generados |
| **ThinkBridges** | Conexiones automáticas entre threads relacionados |
| **Propagación Gossip** | Los bridges se propagan en la red cuando los conceptos evolucionan |
| **GuardCode** | Enforcement del modo plan, protección contra drift |
| **Síntesis 95%** | Preservación automática del contexto antes del compactado |
| **100% Transparente** | Cero acción del usuario requerida |

---

## Arquitectura v2 (Simplificada)

### Solo 2 Entidades

| Entidad | Rol |
|---------|-----|
| **Thread** | Unidad de trabajo = tema + mensajes + resumen + embedding |
| **ThinkBridge** | Conexión semántica entre dos threads |

### Qué Cambió desde v1

| v1 | v2 | Por qué |
|----|----|----|
| Fragments | Absorbidos en Threads | Más simple, cada mensaje = fragmento implícito |
| MemBloc | Thread.status=archived | Modelo unificado |
| Graph complejo | Embeddings + Bridges | Más potente, menos overhead |
| Umbrales hardcodeados | Decisiones LLM | Inteligente, no arbitrario |

---

## Instalación

```bash
# En tu proyecto destino
/ruta/a/.ai_smartness_v2/install.sh .
```

### Configuración Interactiva

1. **Idioma**: Inglés, Francés o Español
2. **Modo**: Heavy, Normal o Light (afecta límites de threads, no el costo de extracción)
3. **Base de datos**: Mantener datos existentes o empezar de cero

### Qué Hace el Script

- Copia .ai_smartness_v2 en tu proyecto
- Configura los hooks de Claude Code con **rutas absolutas**
- Detecta la ruta del CLI Claude para extracción LLM
- Inicializa la estructura de la base de datos
- Añade exclusiones en .gitignore y .claudeignore

**Nota**: La extracción siempre usa **Haiku** (económico, suficiente para extracción semántica). Tu agente principal puede usar cualquier modelo (Opus, Sonnet, etc.) - son independientes.

---

## Comandos CLI

```bash
# Navega a tu proyecto
cd /tu/proyecto

# Vista general del estado
python3 .ai_smartness_v2/cli/main.py status

# Listar threads
python3 .ai_smartness_v2/cli/main.py threads
python3 .ai_smartness_v2/cli/main.py threads --status active
python3 .ai_smartness_v2/cli/main.py threads --limit 20

# Ver thread específico
python3 .ai_smartness_v2/cli/main.py thread <thread_id>

# Listar bridges
python3 .ai_smartness_v2/cli/main.py bridges
python3 .ai_smartness_v2/cli/main.py bridges --thread <thread_id>

# Búsqueda semántica
python3 .ai_smartness_v2/cli/main.py search "autenticación"
```

---

## Cómo Funciona

### 1. Captura (hook PostToolUse)

Cada resultado de herramienta (Read, Write, Task, etc.) es capturado:
```
[Resultado Herramienta] → [Filtro Ruido] → [Extracción LLM] → [Decisión Thread]
```

### 2. Gestión de Threads

El LLM decide para cada input:
- **NEW_THREAD**: Tema diferente → crear nuevo thread
- **CONTINUE**: Mismo tema → añadir al thread activo
- **FORK**: Sub-tema → crear thread hijo
- **REACTIVATE**: Tema antiguo vuelve → despertar thread archivado

### 3. Propagación Gossip

Cuando un thread cambia:
```
Thread A modificado → Recalcular embedding
                    → Para cada thread B conectado
                    → Si similitud alta → propagar bridges a conexiones de B
```

### 4. Inyección (hook UserPromptSubmit)

Antes de cada prompt del usuario, contexto invisible inyectado:
```html
<!-- ai_smartness: {"active_thread": "...", "decisions": [...]} -->
```

### 5. Síntesis (hook PreCompact)

Al 95% de la ventana de contexto:
- El LLM genera una síntesis del estado actual
- Decisiones, preguntas abiertas, threads activos
- Inyectado después del compactado
- El usuario no ve nada

---

## Configuración

Config almacenada en `.ai_smartness_v2/.ai/config.json`:

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

| Modo | Límite Threads | Caso de uso |
|------|----------------|-------------|
| Light | 15 | Proyectos pequeños |
| Normal | 50 | Proyectos medianos |
| Heavy | 100 | Proyectos grandes/complejos (blockchain, empresa) |

**Nota**: El modelo de extracción es siempre Haiku (económico). El modo solo afecta los límites de threads.

---

## Estructura de la Base de Datos

```
.ai_smartness_v2/.ai/
├── config.json           # Configuración
├── db/
│   ├── threads/          # Archivos JSON Thread
│   │   └── thread_*.json
│   ├── bridges/          # Archivos JSON ThinkBridge
│   │   └── bridge_*.json
│   └── synthesis/        # Síntesis de compactado
└── processor.sock        # Socket daemon (cuando activo)
```

---

## Hooks Claude Code

| Hook | Script | Función |
|------|--------|---------|
| `UserPromptSubmit` | inject.py | Inyección de contexto |
| `PostToolUse` | capture.py | Captura automática |
| `PreCompact` | compact.py | Síntesis al 95% |

---

## Reglas GuardCode

| Regla | Descripción |
|-------|-------------|
| `enforce_plan_mode` | Bloquear cambios de código sin plan validado |
| `warn_quick_solutions` | Recordar que simple ≠ mejor |
| `require_all_choices` | Debe presentar todas las alternativas |

---

## Requisitos

- Python 3.10+
- Claude Code (CLI o extensión VS Code)
- sentence-transformers (para embeddings locales)

---

## Solución de Problemas

### Las capturas no funcionan

Verifica las rutas de los hooks en `.claude/settings.json` - deben ser **rutas absolutas**.

### Extracción muestra "heuristic fallback"

CLI Claude no encontrado. Verifica:
```bash
which claude
# Debería devolver /usr/local/bin/claude o similar
```

### Demasiados threads

Aumenta el límite en la config:
```json
"active_threads_limit": 150
```

---

## Licencia

MIT

---

**Nota**: AI Smartness v2 es una reescritura completa enfocada en la simplicidad. La metáfora de red neuronal es operacional, no una implementación neuronal estricta.
