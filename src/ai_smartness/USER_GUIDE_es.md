# AI Smartness v7 - Guía de Usuario

## Inicio Rápido

**Plataforma:** Linux / macOS / Windows (requiere WSL)

> El sistema de hooks requiere rutas Unix absolutas. En Windows, usa WSL (Windows Subsystem for Linux).

### 1. Pre-instalar Dependencias (Recomendado)

sentence-transformers requiere PyTorch. Instala **antes** del script de instalación para elegir CPU o GPU:

```bash
# Solo CPU (no requiere GPU, más ligero)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers

# O con soporte CUDA (más rápido si tienes GPU NVIDIA)
pip install torch && pip install sentence-transformers
```

Si omites este paso, el instalador instalará automáticamente la versión por defecto (CPU).

### 2. Ejecutar Instalación

```bash
/ruta/a/ai_smartness-DEV/install.sh /ruta/a/tu/proyecto
```

El instalador:
- Preguntará idioma (en/fr/es) y modo (MAX/Heavy/Normal/Light)
- Copiará archivos, configurará hooks, iniciará el daemon en segundo plano
- Instalará el comando CLI `ai`

### 3. Trabaja Normalmente

El sistema captura todo automáticamente. Verifica el estado en cualquier momento:
```bash
ai status
```
¡O escribe `ai status` directamente en tu prompt!

Eso es todo. El sistema es 100% transparente.

---

## Entendiendo el Modelo de Asociación

AI Smartness no es un "sistema de control" para tu agente - es una **capa de mejora cognitiva** que permite una asociación real.

### ¿Qué Hace una Buena Asociación?

| Enfoque Tradicional | Enfoque de Asociación |
|---------------------|----------------------|
| Reglas rígidas impuestas | Guidelines comprendidas |
| Prevenir todos los errores | Aprender del contexto |
| Controlar comportamiento | Habilitar capacidades |
| Desconfianza por defecto | Confianza por experiencia |

### Tu Rol como Usuario

No eres un "supervisor" corrigiendo un sistema poco confiable. Eres un **socio** trabajando con un agente inteligente que:

- Tiene su propio sistema de memoria
- Puede gestionar su propio contexto
- Aprende tus preferencias con el tiempo
- Toma decisiones basadas en el contexto

### Primeras Sesiones con un Nuevo Agente

Las primeras sesiones son cruciales. Durante este tiempo:

1. **Deja que el agente explore** - No restrinjas inmediatamente
2. **Expresa preferencias naturalmente** - "Prefiero X" en vez de "Siempre debes X"
3. **Observa lo que emerge** - El agente puede desarrollar hábitos útiles
4. **Guía suavemente** - Redirige en lugar de prohibir

El objetivo es un agente que *entiende* las buenas prácticas, no uno que sigue reglas ciegamente.

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

### SharedThreads (v6.0)

Un **SharedThread** es una instantánea de solo lectura de un thread publicado en la red para compartir entre agentes.

| Propiedad | Descripción |
|-----------|-------------|
| `shared_id` | Identificador único de la instantánea compartida |
| `owner_agent` | Agente que publicó el thread |
| `visibility` | `network` (todos los agentes) o `restricted` (agentes específicos) |
| `snapshot` | Copia del contenido del thread al momento de publicar |

Los SharedThreads mantienen el aislamiento de memoria - el thread original permanece privado.

### Subscriptions (v6.0)

Una **Subscription** es una copia local en caché de un SharedThread de otro agente.

| Propiedad | Descripción |
|-----------|-------------|
| `shared_id` | El SharedThread al que está suscrito |
| `local_copy` | Instantánea en caché de solo lectura |
| `last_synced` | Timestamp de la última sincronización |
| `stale` | True si el propietario ha publicado actualizaciones |

Usa `ai_sync()` para obtener actualizaciones de suscripciones obsoletas.

### InterAgentBridges (v6.0)

Un **InterAgentBridge** es una conexión semántica entre threads de diferentes agentes.

| Propiedad | Descripción |
|-----------|-------------|
| `source_shared_id` | SharedThread del agente que propone |
| `target_shared_id` | SharedThread del agente que acepta |
| `strength` | Puntuación de similitud semántica |
| `status` | `pending`, `accepted`, `rejected` |
| `ttl` | Tiempo de vida (24h por defecto) |

Requiere consentimiento bilateral - ambos agentes deben aceptar la conexión.

### Aislamiento de Memoria Multi-Agente (v7.0)

AI Smartness v7.0 soporta **aislamiento de memoria** para múltiples agentes trabajando en el mismo proyecto.

| Modo | Descripción | Ruta de Almacenamiento |
|------|-------------|------------------------|
| **Simple** | Memoria compartida única (defecto) | `.ai/db/` |
| **Multi** | Memorias aisladas por agente | `.ai/db/agents/{agent_id}/` |

**Funcionamiento:**
1. **Activación**: La instalación de `mcp_smartness` establece `project_mode=multi` en `.mcp_smartness_agent`
2. **Registro de Agente**: Cada agente recibe un `agent_id` único (ej: "Cog", "Com", "Kratos")
3. **Enrutamiento de Almacenamiento**: El sistema enruta todas las operaciones a la partición del agente
4. **Detección ENV**: Variable de entorno `AI_SMARTNESS_AGENT_ID` o auto-detección
5. **Límite**: Máximo 5 agentes por proyecto para rendimiento

**¿Por qué aislamiento?**
- Cada agente se especializa (backend, frontend, infra, etc.)
- Sin mezcla de contextos entre agentes
- Memoria más enfocada y eficiente
- Rendimiento optimizado (embeddings, daemon por agente)

**Cognición compartida mantenida**: `ai_share()`/`ai_subscribe()` siguen funcionando para compartir conocimiento entre agentes, el aislamiento solo concierne a las memorias privadas de cada agente.

### Reglas de Usuario

El sistema detecta y recuerda tus preferencias. Di cosas como:
- "recuerda: siempre usar TypeScript"
- "regla: sin commits directos a main"
- "siempre hacer un plan antes de implementar"
- "nunca usar console.log en producción"

Estas reglas se almacenan permanentemente y se inyectan en cada prompt.

---

## Herramientas MCP del Agente (v6.0)

Tu agente tiene acceso a herramientas MCP nativas para gestión de memoria:

### Recall Activo

```
ai_recall(query="autenticacion")
```

Busca en la memoria por palabra clave o tema. Devuelve threads coincidentes con resúmenes, topics y bridges relacionados.

**Ejemplos:**
- `ai_recall(query="solana")` - Todo sobre Solana
- `ai_recall(query="hooks")` - Memoria sobre hooks
- `ai_recall(query="autenticacion")` - Trabajo relacionado con auth
- `ai_recall(query="thread_abc123")` - Thread específico por ID

### Fusionar Threads

```
ai_merge(survivor_id="t1", absorbed_id="t2")
```

Combina dos threads relacionados para liberar contexto. El survivor absorbe:
- Todos los mensajes (ordenados por timestamp)
- Topics y tags (unión)
- Boost de weight (+0.1)

El thread absorbido se archiva con el tag `merged_into:<survivor_id>`.

**Nota:** Los threads split-locked no pueden ser absorbidos.

### Dividir Threads

Workflow de dos pasos cuando un thread ha derivado hacia múltiples temas:

**Paso 1 - Obtener info del thread:**
```
ai_split(thread_id="abc")
```
Devuelve lista de mensajes con sus IDs.

**Paso 2 - Confirmar split:**
```
ai_split(thread_id="abc", confirm=True, titles=["T1", "T2"], message_groups=[["m1", "m2"], ["m3", "m4"]])
```

**Modos de bloqueo:**
| Modo | Descripción |
|------|-------------|
| `compaction` | Auto-desbloqueo en el próximo compactado (defecto) |
| `agent_release` | Desbloqueo manual via `ai_unlock()` |
| `force` | Nunca auto-desbloqueo |

### Desbloquear Threads

```
ai_unlock(thread_id="abc")
```

Elimina la protección split-lock, permitiendo que el thread sea fusionado.

### Ayuda & Estado

```
ai_help()    # Documentación completa del agente
ai_status()  # Estado de memoria (threads, bridges, % contexto)
```

Útil cuando el agente necesita recordar sus capacidades o verificar el estado actual de la memoria.

### Operaciones Batch (v5.2)

Realizar múltiples operaciones eficientemente:

```
ai_merge_batch(operations=[
    {"survivor_id": "t1", "absorbed_id": "t2"},
    {"survivor_id": "t3", "absorbed_id": "t4"}
])

ai_rename_batch(operations=[
    {"thread_id": "t1", "new_title": "Nuevo Título 1"},
    {"thread_id": "t2", "new_title": "Nuevo Título 2"}
])
```

### Herramientas de Limpieza (v5.1.2+)

Corregir threads con títulos malos o faltantes:

```
ai_cleanup()                     # Auto-corrección con heurísticas
ai_cleanup(mode="interactive")   # Revisar antes de corregir
ai_rename(thread_id, new_title)  # Renombrar un thread
```

### V6.0 Cognición Compartida (Memoria Inter-Agentes)

Compartir conocimiento con otros agentes manteniendo el aislamiento de memoria:

```
ai_share(thread_id)           # Compartir un thread en la red
ai_unshare(shared_id)         # Eliminar compartición de un thread
ai_publish(shared_id)         # Publicar actualización a suscriptores
ai_discover(topics=["rust"])  # Encontrar threads compartidos por topics
ai_subscribe(shared_id)       # Suscribirse a un thread compartido
ai_unsubscribe(shared_id)     # Desuscribirse de un thread compartido
ai_sync()                     # Sincronizar todas las suscripciones obsoletas
ai_shared_status()            # Mostrar estado de la cognición compartida
```

**Principios de Aislamiento de Memoria:**
- **Copy-on-share**: La publicación crea una instantánea de solo lectura
- **Pull no push**: Los suscriptores recuperan explícitamente vía `ai_sync()`
- **Sin fuga privada**: Solo IDs de SharedThread, nunca IDs de threads privados

---

## CLI en el Prompt (v3.0.0+)

Escribe comandos CLI directamente en tu prompt y se ejecutarán automáticamente:

```
Tú: ai status
Claude: [Muestra el estado de memoria desde CLI]

Tú: ai threads
Claude: [Lista threads activos]

Tú: ai search authentication
Claude: [Muestra resultados de búsqueda para "authentication"]
```

**Comandos soportados:** `ai status`, `ai threads`, `ai thread <id>`, `ai bridges`, `ai search <query>`, `ai health`, `ai daemon`, `ai mode`, `ai help`

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
ai threads --prune            # Aplicar decay y suspender threads débiles
```

### `ai thread <id>`

Muestra detalles del thread:
```bash
ai thread abc123
```

### `ai bridges`

Lista conexiones semánticas:
```bash
ai bridges                    # Todos los bridges
ai bridges --thread abc123    # Bridges para thread específico
ai bridges --limit 50         # Limitar resultados
ai bridges --prune            # Aplicar decay y eliminar bridges muertos
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

### `ai daemon`

Control del daemon en segundo plano:
```bash
ai daemon           # Muestra estado (defecto)
ai daemon status    # Muestra estado
ai daemon start     # Inicia daemon
ai daemon stop      # Detiene daemon
```

### `ai mode`

Ver o cambiar el modo de operación:
```bash
ai mode             # Muestra modo actual
ai mode light       # Cambia a modo light (15 threads)
ai mode normal      # Cambia a modo normal (50 threads)
ai mode heavy       # Cambia a modo heavy (100 threads)
ai mode max         # Cambia a modo max (200 threads)
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
Verificación: ¿Es una nueva sesión?
         ↓
Si NUEVA SESIÓN:
  - Inyectar vista general de capacidades
  - Mostrar último thread activo ("hot thread")
  - Sugerir recall si el mensaje coincide con topics
         ↓
Siempre:
  - Memory Retriever encuentra threads relevantes (por similitud)
  - Reactivación auto de threads suspendidos si son relevantes
         ↓
Cadena de contexto construida e inyectada
         ↓
Claude recibe tu mensaje + contexto
```

### Seguimiento de Contexto (v4.3)

Monitoreo de contexto en tiempo real con throttle adaptativo:

| Contexto % | Comportamiento |
|------------|----------------|
| < 70% | Actualización cada 30 segundos |
| ≥ 70% | Actualización solo en delta de 5% |

Esto evita llamadas API innecesarias mientras mantiene al agente consciente de la presión sobre el contexto.

### Reactivación Automática de Threads

Cuando mencionas un tema relacionado con un thread suspendido, el sistema puede reactivarlo automáticamente:

| Similitud | Acción |
|-----------|--------|
| > 0.35 | Reactivación auto (alta confianza) |
| 0.15 - 0.35 | LLM Haiku decide (zona borderline) |
| < 0.15 | Sin reactivación |

### Sistema de Decay Neural

Los threads y bridges usan un sistema de peso inspirado en redes neuronales (aprendizaje Hebbiano):

| Acción | Efecto en Weight |
|--------|------------------|
| Nuevo thread | Empieza en 1.0 |
| Fork thread | Hereda weight del padre |
| Cada uso (mensaje) | +0.1 boost (máx 1.0) |
| Decay temporal | Se divide por 2 cada 7 días |
| Por debajo de 0.1 | Thread auto-suspendido |
| Por debajo de 0.05 | Bridge auto-eliminado |

---

## Buenas Prácticas

### Deja que Trabaje

No intentes "ayudar" al sistema:
- Trabaja normalmente
- El sistema captura todo automáticamente
- Los threads se forman naturalmente según tu trabajo

### Expresa Preferencias Naturalmente

En lugar de reglas rígidas, expresa preferencias:
- "Prefiero programación funcional"
- "Siempre añadimos tests para funciones nuevas"
- "No me gusta usar any como tipo"

Se almacenan y aplican naturalmente.

### Confía en el Proceso de Aprendizaje

Las primeras sesiones enseñan los fundamentos. Con el tiempo:
- El agente aprende tus patrones
- La gestión del contexto mejora
- La asociación se profundiza

### Sobre GuardCode

GuardCode es un **asesor**, no un ejecutor. Él:
- Sugiere planificar antes de implementar
- Recuerda buenas prácticas
- Anima a presentar opciones

**No** hace:
- Garantizar comportamiento específico
- Prevenir todos los errores
- Anular el juicio del agente

Si tu agente toma una decisión con la que no estás de acuerdo, discútelo. Así funcionan las asociaciones.

### Gestión Proactiva del Contexto

Un agente maduro raramente debería llegar al compactado. Anima esto:
1. Enseñando merge/split temprano
2. Apreciando cuando el agente gestiona el contexto
3. Confiando en las decisiones del agente sobre qué mantener/archivar

---

## Configuración

### Ubicación

`ai_smartness/.ai/config.json`

### Configuraciones Clave

```json
{
  "version": "6.0.2",
  "settings": {
    "thread_mode": "heavy",
    "active_threads_limit": 100,
    "shared_cognition": {
      "enabled": true,
      "auto_notify_mcp_smartness": true,
      "bridge_proposal_ttl_hours": 24,
      "default_visibility": "network"
    }
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

---

## Solución de Problemas

### "Daemon not running"

```bash
ai daemon start
```

Si falla, verifica logs:
```bash
cat ai_smartness/.ai/daemon_stderr.log
```

### El agente no usa recall

Esto es normal para agentes nuevos. Necesitan descubrir sus herramientas:
1. Puedes mencionarlo: "Puedes usar `ai_recall()` para buscar en tu memoria"
2. Apunta a `ai_help()`
3. Confía en que aprenderán con las sesiones

### El agente compacta demasiado

El agente debería aprender a gestionar el contexto proactivamente. Si el compactado ocurre frecuentemente:
1. Discute la gestión de contexto con el agente
2. Anima el uso de merge/split
3. Verifica si el modo es apropiado (quizás aumentar a MAX)

### Memoria no inyectada

Verifica logs de inyección:
```bash
tail -20 ai_smartness/.ai/inject.log
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
| `.ai/heartbeat.json` | Seguimiento sesión, % contexto |
| `.ai/processor.pid` | ID del proceso daemon |
| `.ai/processor.sock` | Socket del daemon |
| `.ai/processor.log` | Logs del daemon |
| `.ai/inject.log` | Logs de inyección |
| `.ai/db/threads/*.json` | Datos de threads |
| `.ai/db/bridges/*.json` | Datos de bridges |
| `.ai/db/synthesis/*.json` | Síntesis de compactado |
| `.ai/db/shared/published/*.json` | SharedThreads de este agente |
| `.ai/db/shared/subscriptions/*.json` | Suscripciones a SharedThreads de otros agentes |
| `.ai/db/shared/cross_bridges/*.json` | InterAgentBridges (consentimiento bilateral) |
| `.ai/db/shared/proposals/` | Propuestas de bridges pendientes (incoming/outgoing) |

---

## El Viaje de la Asociación

| Fase | Qué Esperar |
|------|-------------|
| **Sesiones 1-3** | El agente descubre herramientas, construye memoria inicial |
| **Sesiones 4-10** | Emergen patrones, preferencias se solidifican |
| **Sesiones 10+** | Asociación madura, gestión proactiva del contexto |
| **Largo plazo** | El agente raramente compacta, gestiona memoria expertamente |

La mejor indicación de que AI Smartness funciona no es que nada salga mal - es que tu agente se convierte en un mejor colaborador con el tiempo.

---

## Lo que AI Smartness NO Hace

| Funcionalidad | Por qué No |
|---------------|------------|
| Garantizar comportamiento | Consultivo, no imposición |
| Requerir acción del usuario | 100% transparente |
| Almacenar contenido de código | Solo semántica, no código completo |
| Enviar datos externamente | 100% local |
| Modificar tu código | Sistema de memoria de solo lectura |
| Reemplazar tu juicio | Asociación, no reemplazo |

---

## Soporte

Si encuentras problemas:
1. Ejecuta `ai health` para diagnosticar
2. Verifica logs en `ai_smartness/.ai/`
3. Verifica hooks en `.claude/settings.json`
4. Intenta `ai daemon stop && ai daemon start`

Recuerda: Muchos "problemas" son en realidad el agente aprendiendo. Dale tiempo antes de hacer troubleshooting.
