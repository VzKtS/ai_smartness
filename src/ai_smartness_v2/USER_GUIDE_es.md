# AI Smartness v2 - Guía de Usuario

## Inicio Rápido

1. **Instala** en tu proyecto:
   ```bash
   /ruta/a/ai_smartness_v2-DEV/install.sh /ruta/a/tu/proyecto
   ```

2. **Trabaja normalmente** - el sistema captura todo automáticamente

3. **Verifica el estado** en cualquier momento:
   ```bash
   ai status
   ```

Eso es todo. El sistema es 100% transparente.

---

## Conceptos Clave

### Threads

Un **Thread** es una unidad de trabajo semántica que representa un tema o tarea.

| Estado | Descripción |
|--------|-------------|
| `active` | Actualmente en trabajo |
| `suspended` | En pausa, puede reactivarse |
| `archived` | Completado o dormido |

Los threads contienen:
- **Título**: Título semántico auto-generado
- **Mensajes**: Historial de interacciones
- **Resumen**: Resumen auto-generado
- **Topics**: Conceptos clave extraídos
- **Embedding**: Vector para búsqueda por similitud

### ThinkBridges

Un **ThinkBridge** es una conexión semántica entre dos threads.

| Tipo | Significado |
|------|-------------|
| `extends` | A extiende/refina B |
| `depends` | A depende de B |
| `contradicts` | A y B están en tensión |
| `replaces` | A reemplaza B |
| `child_of` | A es un subtema de B |

Los bridges se crean automáticamente cuando el sistema detecta similitud semántica.

### Reglas de Usuario

El sistema detecta y recuerda tus preferencias. Di cosas como:
- "recuerda: siempre usar TypeScript"
- "regla: sin commits directos a main"
- "siempre hacer un plan antes de implementar"
- "nunca usar console.log en producción"

Estas reglas se almacenan permanentemente y se inyectan en cada prompt.

---

## Referencia CLI

### `ai status`

Muestra la vista general global:
```
=== AI Smartness Status ===
Project: MiProyecto

Threads: 45 total
  Active:    12
  Suspended: 33
  Archived:  0

Bridges: 234 connections

Last activity: 2026-01-29 15:30:22
Current thread: "Sistema de Autenticación"
```

### `ai threads`

Lista threads con filtrado:
```bash
ai threads                    # Threads activos (defecto)
ai threads --status active    # Solo activos
ai threads --status suspended # Solo suspendidos
ai threads --status all       # Todos los threads
ai threads --limit 20         # Limitar a 20 resultados
```

### `ai thread <id>`

Muestra detalles de un thread:
```bash
ai thread abc123
```

### `ai bridges`

Lista conexiones semánticas:
```bash
ai bridges                    # Todos los bridges
ai bridges --thread abc123    # Bridges para thread específico
ai bridges --limit 50         # Limitar resultados
```

### `ai search`

Búsqueda semántica en todos los threads:
```bash
ai search "autenticación"
ai search "migración base de datos" --limit 10
```

### `ai health`

Verificación de salud del sistema:
```bash
ai health
```

Salida:
```
=== AI Smartness Health ===
Threads: 158 (100 active, 58 suspended)
Bridges: 3374
Continuation rate: 23.4%
Embedding coverage: 100.0%
Daemon: Running (PID 12345)
```

**Métricas clave:**
- **Continuation rate**: % de threads con >1 mensaje (más alto es mejor)
- **Embedding coverage**: % de threads con embeddings válidos (debería ser 100%)
- **Daemon**: Debería ser "Running"

### `ai reindex`

Recalcula todos los embeddings:
```bash
ai reindex           # Estándar
ai reindex --verbose # Con detalles de progreso
```

Usar después de:
- Instalar sentence-transformers
- Actualizar AI Smartness
- Si embedding coverage es < 100%

### `ai daemon`

Control del daemon en segundo plano:
```bash
ai daemon           # Muestra estado (defecto)
ai daemon status    # Muestra estado
ai daemon start     # Inicia daemon
ai daemon stop      # Detiene daemon
```

---

## Cómo Funciona la Memoria

### Flujo de Captura

```
Usas una herramienta (Read, Write, etc.)
         ↓
El hook PostToolUse se dispara
         ↓
Contenido enviado al daemon (rápido, no bloqueante)
         ↓
Daemon extrae semántica (LLM)
         ↓
Decisión thread: NEW / CONTINUE / FORK / REACTIVATE
         ↓
Thread actualizado, bridges recalculados
```

### Flujo de Inyección

```
Escribes un mensaje
         ↓
El hook UserPromptSubmit se dispara
         ↓
Memory Retriever encuentra threads relevantes (por similitud)
         ↓
Reactivación automática de threads suspendidos si son relevantes
         ↓
Cadena de contexto construida:
  - Título + resumen del thread actual
  - Threads relacionados (via bridges)
  - Reglas de usuario
         ↓
Inyectado como <system-reminder> invisible
         ↓
Claude recibe tu mensaje + contexto
```

### Reactivación Automática de Threads

Cuando mencionas un tema relacionado con un thread suspendido, el sistema puede reactivarlo automáticamente:

| Similitud | Acción |
|-----------|--------|
| > 0.35 | Reactivación auto (alta confianza) |
| 0.15 - 0.35 | LLM Haiku decide (zona borderline) |
| < 0.15 | Sin reactivación |

**Ejemplo:** Si trabajaste en "sistema de memoria IA" ayer (ahora suspendido), y hoy preguntas:
> "cuéntame sobre la capa de meta cognición"

El sistema:
1. Calcula la similitud con "sistema de memoria IA" (borderline: 0.28)
2. Consulta a Haiku: "¿Este mensaje está relacionado con este thread?"
3. Haiku confirma la relación semántica
4. Reactiva el thread
5. Inyecta el contexto en tu conversación

**Liberación de Slots:** Si estás en el máximo de threads activos (ej: 100/100), el sistema suspende automáticamente el thread activo menos importante para hacer espacio al thread reactivado.

### Qué se Inyecta

Ejemplo de inyección (invisible para ti):
```xml
<system-reminder>
AI Smartness Memory Context:

Current thread: "Autenticación JWT"
Summary: Implementando rotación de refresh tokens con almacenamiento Redis.

Related threads:
- "Esquema Base de Datos" - Tablas de usuarios y sesiones
- "Auditoría Seguridad" - Políticas de expiración de tokens

User rules:
- siempre hacer un plan antes de implementar
- usar modo estricto TypeScript
</system-reminder>

Tu mensaje real aquí...
```

---

## Buenas Prácticas

### Deja que el Sistema Trabaje

No intentes "ayudar" al sistema:
- Trabaja normalmente
- El sistema captura todo automáticamente
- Los threads se forman naturalmente según tu trabajo

### Expresa tus Preferencias

Dile al agente tus reglas:
- "recuerda: prefiero programación funcional"
- "regla: siempre añadir tests para funciones nuevas"
- "nunca usar any como tipo"

Se almacenan y aplican a todas las sesiones futuras.

### Verifica la Salud Regularmente

```bash
ai health
```

- Tasa de continuación < 10%? Verifica embeddings
- Daemon detenido? Ejecuta `ai daemon start`
- Cobertura embeddings < 100%? Ejecuta `ai reindex`

### Reanudación de Sesión

Cuando inicias una nueva sesión:
1. La memoria se inyecta automáticamente
2. Verifica estado: `ai status`
3. Tu agente "recuerda" el contexto anterior

---

## Configuración

### Ubicación

`ai_smartness_v2/.ai/config.json`

### Configuraciones Clave

```json
{
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100
  },
  "guardcode": {
    "enforce_plan_mode": true,
    "warn_quick_solutions": true,
    "require_all_choices": true
  }
}
```

### Comparación de Modos

| Modo | Límite Threads | Ideal Para |
|------|----------------|------------|
| MAX | 200 | Proyectos complejos, sesiones 15+ horas |
| heavy | 100 | Codebases grandes, proyectos largos |
| normal | 50 | Proyectos medianos |
| light | 15 | Scripts pequeños, tareas rápidas |

El modo **MAX** es recomendado para:
- Proyectos con muchos componentes interdependientes
- Sesiones de trabajo muy largas (15+ horas)
- Casos donde la pérdida de memoria sería crítica

---

## Solución de Problemas

### "Daemon not running"

```bash
ai daemon start
```

Si falla, verifica logs:
```bash
cat ai_smartness_v2/.ai/daemon_stderr.log
```

### "Heuristic fallback" en títulos

CLI Claude no encontrado. Verifica:
```bash
which claude
```

Actualiza la ruta en config si es necesario.

### Tasa de continuación baja

¿Los threads no se consolidan? Verifica:
1. ¿Está instalado sentence-transformers?
   ```bash
   python3 -c "import sentence_transformers; print('OK')"
   ```
2. Si no: `pip install sentence-transformers`
3. Reinicia daemon: `ai daemon stop && ai daemon start`
4. Reindexar: `ai reindex`

### Memoria no inyectada

Verifica logs de inyección:
```bash
tail -20 ai_smartness_v2/.ai/inject.log
```

Debería mostrar líneas como:
```
[2026-01-29 15:30:22] Injected: 450 chars (380 memory) for: Cómo hago...
```

### Hooks no se disparan

Verifica `.claude/settings.json`:
- Las rutas deben ser **absolutas**
- Python3 debe estar en PATH

---

## Referencia de Archivos

| Archivo | Propósito |
|---------|-----------|
| `.ai/config.json` | Configuración |
| `.ai/user_rules.json` | Tus reglas almacenadas |
| `.ai/processor.pid` | ID del proceso daemon |
| `.ai/processor.sock` | Socket del daemon |
| `.ai/processor.log` | Logs del daemon |
| `.ai/inject.log` | Logs de inyección |
| `.ai/db/threads/*.json` | Datos de threads |
| `.ai/db/bridges/*.json` | Datos de bridges |
| `.ai/db/synthesis/*.json` | Síntesis de compactado |

---

## Lo que AI Smartness NO Hace

| Funcionalidad | Por qué No |
|---------------|------------|
| Requiere acción del usuario | 100% transparente |
| Almacena contenido de código | Solo semántica, no código completo |
| Envía datos externamente | 100% local |
| Modifica tu código | Sistema de memoria de solo lectura |
| Requiere configuración | Funciona out of the box |

---

## Soporte

Si encuentras problemas:
1. Ejecuta `ai health` para diagnosticar
2. Verifica logs en `ai_smartness_v2/.ai/`
3. Verifica hooks en `.claude/settings.json`
4. Intenta `ai daemon stop && ai daemon start`
