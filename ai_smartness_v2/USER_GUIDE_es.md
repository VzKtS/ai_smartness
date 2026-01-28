# AI Smartness v2 - Guía de Usuario

## Visión General

AI Smartness v2 es un sistema de memoria persistente para Claude Code. Captura automáticamente tu contexto de trabajo, lo organiza en threads semánticos, y mantiene las conexiones entre conceptos relacionados.

**Principio clave**: 100% transparente - no necesitas hacer nada especial. Trabaja normalmente.

---

## Conceptos Clave

### Threads

Un **Thread** es una unidad de trabajo semántica que representa un tema o tarea:

| Status | Descripción |
|--------|-------------|
| `active` | Actualmente en trabajo |
| `suspended` | En pausa, puede reactivarse |
| `archived` | Completado o dormido |

Los threads contienen:
- **Título**: Título semántico generado por LLM
- **Mensajes**: Historial de interacciones
- **Resumen**: Resumen generado por LLM
- **Embedding**: Vector para búsqueda por similitud

### ThinkBridges

Un **ThinkBridge** es una conexión semántica entre dos threads.

Tipos de bridges:
| Tipo | Significado |
|------|-------------|
| `extends` | A extiende/refina B |
| `depends` | A depende de B |
| `contradicts` | A y B están en tensión |
| `replaces` | A reemplaza B |
| `child_of` | A es un subtema de B |

Los bridges se crean automáticamente cuando el sistema detecta similitud semántica entre threads.

### Propagación Gossip

Cuando un thread cambia, sus conexiones **se propagan** a través de la red:
- Thread A modificado → sus bridges son evaluados
- Si alta similitud con threads conectados → nuevos bridges creados
- Crea una "red de conocimiento" que crece orgánicamente

---

## Cómo Funciona (Entre bastidores)

### 1. Captura

Cada resultado de herramienta (Read, Write, Task, Bash, etc.) es capturado y procesado:
1. **Filtro de ruido**: Elimina tags IDE, números de línea, formateo
2. **Extracción LLM**: Extrae intención, temas, preguntas
3. **Decisión de thread**: ¿Nuevo thread? ¿Continuar existente? ¿Fork?

### 2. Gestión de Threads

El LLM decide qué hacer con cada input:

| Decisión | Cuándo |
|----------|--------|
| `NEW_THREAD` | Tema diferente de los threads activos |
| `CONTINUE` | Mismo tema que el thread activo |
| `FORK` | Subtema del thread activo |
| `REACTIVATE` | Tema antiguo que vuelve |

### 3. Inyección de Contexto

Antes de cada uno de tus prompts, se inyecta contexto invisible:
- Info del thread activo
- Decisiones recientes
- Recordatorios GuardCode

Nunca ves esto, pero ayuda al agente a mantener coherencia.

### 4. Síntesis al 95%

Cuando la ventana de contexto se llena al 95%:
1. El LLM genera una síntesis del estado actual
2. Decisiones clave, preguntas abiertas, trabajo activo
3. La síntesis se inyecta después del compactado
4. No ves nada - el contexto se preserva

---

## Comandos CLI

### Estado

```bash
# Vista general global
python3 _ai_smartness_v2/cli/main.py status
```

Muestra:
- Conteo de threads por estado
- Conteo de bridges
- Última actividad
- Título del thread activo

### Threads

```bash
# Listar todos los threads
python3 _ai_smartness_v2/cli/main.py threads

# Filtrar por estado
python3 _ai_smartness_v2/cli/main.py threads --status active
python3 _ai_smartness_v2/cli/main.py threads --status suspended
python3 _ai_smartness_v2/cli/main.py threads --status archived

# Limitar resultados
python3 _ai_smartness_v2/cli/main.py threads --limit 10

# Ver thread específico
python3 _ai_smartness_v2/cli/main.py thread thread_20260128_143022_abc123
```

### Bridges

```bash
# Listar todos los bridges
python3 _ai_smartness_v2/cli/main.py bridges

# Filtrar por thread
python3 _ai_smartness_v2/cli/main.py bridges --thread thread_20260128_143022

# Limitar resultados
python3 _ai_smartness_v2/cli/main.py bridges --limit 20
```

### Búsqueda

```bash
# Búsqueda semántica en threads
python3 _ai_smartness_v2/cli/main.py search "autenticación"
python3 _ai_smartness_v2/cli/main.py search "migración base de datos"

# Limitar resultados
python3 _ai_smartness_v2/cli/main.py search "api" --limit 5
```

---

## GuardCode

GuardCode protege tu proceso de desarrollo con reglas configurables.

### Reglas por Defecto

| Regla | Efecto |
|-------|--------|
| `enforce_plan_mode` | Bloquea cambios de código sin plan validado |
| `warn_quick_solutions` | Recuerda que simple ≠ mejor |
| `require_all_choices` | Debe presentar todas las alternativas |

### Cómo Funciona

Antes de cada prompt, GuardCode verifica:
1. ¿Hay un plan activo para este trabajo?
2. ¿Ha sido validado el plan por el usuario?
3. ¿Hay alternativas que deberían presentarse?

Si se violan las reglas, se inyectan recordatorios en el contexto.

### Configuración

Edita `_ai_smartness_v2/.ai/config.json`:

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

## Buenas Prácticas

### Deja que el Sistema Trabaje

No intentes "ayudar" al sistema - captura todo automáticamente. Simplemente:
- Trabaja normalmente
- Toma decisiones explícitamente cuando se te pida
- Deja que los threads se formen naturalmente

### Reanudación de Sesión

Cuando inicias una nueva sesión:
1. El sistema inyecta contexto automáticamente
2. Puedes verificar el estado: `python3 _ai_smartness_v2/cli/main.py status`
3. Tu agente tendrá acceso al contexto anterior

### Proyectos Largos

Para proyectos que abarcan semanas/meses:
- Los threads acumulan conocimiento
- Los bridges conectan trabajo relacionado
- El contexto se sintetiza al 95%
- La reanudación es fluida

### Proyectos Grandes

Para codebases grandes (blockchain, empresa):
- Aumenta el límite de threads en la config
- El modo "heavy" soporta hasta 100 threads
- Edita la config para ir más alto si es necesario

---

## Configuración

### Límites de Threads

```json
{
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100
  }
}
```

| Modo | Límite por defecto | Uso típico |
|------|-------------------|------------|
| light | 15 | Proyectos pequeños |
| normal | 50 | Proyectos medianos |
| heavy | 100 | Proyectos grandes/complejos |

### Modelo de Extracción

```json
{
  "llm": {
    "extraction_model": "claude-3-5-haiku-20241022",
    "claude_cli_path": "/usr/local/bin/claude"
  }
}
```

La extracción siempre usa Haiku (económico). Esto es independiente del modelo de tu agente principal.

---

## Solución de Problemas

### "Heuristic fallback" en títulos

El CLI de Claude no fue encontrado. Verifica:
```bash
which claude
```

Si no se encuentra, instala el CLI de Claude Code o actualiza la ruta en la config.

### Las capturas no ocurren

Verifica los hooks en `.claude/settings.json`:
- Las rutas deben ser **absolutas**
- Python3 debe estar en el PATH

### Demasiados threads

Aumenta el límite:
```json
"active_threads_limit": 150
```

### Drift de contexto

Si el agente parece "olvidar" contexto:
1. Verifica el estado de los threads: los threads activos tienen contexto
2. Verifica los bridges: los threads relacionados deberían estar conectados
3. La síntesis al 95% preserva info clave

---

## Archivos de Base de Datos

Ubicación: `_ai_smartness_v2/.ai/`

| Archivo/Carpeta | Contenido |
|-----------------|-----------|
| `config.json` | Configuración |
| `db/threads/` | Archivos JSON de Thread |
| `db/bridges/` | Archivos JSON de Bridge |
| `db/synthesis/` | Síntesis de compactado |

### Inspección Manual

```bash
# Contar threads
ls _ai_smartness_v2/.ai/db/threads/ | wc -l

# Contar bridges
ls _ai_smartness_v2/.ai/db/bridges/ | wc -l

# Ver un thread
cat _ai_smartness_v2/.ai/db/threads/thread_20260128_143022_abc123.json | python3 -m json.tool
```

---

## Lo que v2 NO Hace

| Funcionalidad | Por qué No |
|---------------|------------|
| Requiere acción del usuario | 100% transparente |
| Usa regex para semántica | Solo LLM para significado |
| Hardcodea umbrales | El LLM decide inteligentemente |
| Contamina tus prompts | El contexto es invisible |
| Requiere configuración | Funciona out of the box |

---

## Soporte

Si encuentras problemas:
1. Verifica `.claude/settings.json` para rutas de hooks correctas
2. Verifica que el CLI de Claude sea accesible
3. Revisa los conteos de thread/bridge con el CLI
4. Verifica `_ai_smartness_v2/.ai/` para integridad de la base
