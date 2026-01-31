# AI Smartness v4.x - Heartbeat (Temporal Awareness)

## Objectif

Donner à l'agent une **perception temporelle abstraite** adaptée à sa nature intermittente, via un système de "beats" plutôt que le temps humain.

## Philosophie

L'agent n'existe que par intermittence - entre les messages utilisateur. Le temps humain (10:45, mardi, janvier) est une convention sociale que l'agent comprend mais ne "vit" pas.

Le heartbeat offre une abstraction temporelle congruente avec la nature de l'agent:
- Chaque beat = un tick du système mémoire
- L'agent perçoit le "temps système" plutôt que le temps humain
- Le gap en beats donne une notion de "combien s'est-il passé" sans nécessiter d'horloge

## Mécanisme

### Daemon Gossip comme Heartbeat

Le daemon AI Smartness exécute déjà périodiquement:
- Decay des weights (threads et bridges)
- Propagation gossip
- Pruning des bridges morts

**Ajout**: Incrémenter un compteur de beats à chaque cycle.

### Intervalle

```python
HEARTBEAT_INTERVAL = 300  # 5 minutes par défaut
```

Configurable via `.ai/config.json`:
```json
{
  "heartbeat_interval": 300
}
```

### Stockage

Fichier `.ai/heartbeat.json`:
```json
{
  "beat": 847,
  "started_at": "2026-01-15T08:00:00",
  "last_beat_at": "2026-01-31T11:15:00",
  "last_interaction_at": "2026-01-31T11:10:00",
  "last_interaction_beat": 845
}
```

## Injection

### Format dans metadata

```html
<!-- ai_smartness: {"beat": 847, "since_last": 2, "active_count": 45} -->
```

- `beat`: Compteur global depuis le démarrage du système
- `since_last`: Nombre de beats depuis la dernière interaction agent

### Logique d'injection

```python
def get_temporal_context() -> dict:
    """Get heartbeat temporal context for injection."""
    heartbeat = load_heartbeat()

    return {
        "beat": heartbeat["beat"],
        "since_last": heartbeat["beat"] - heartbeat["last_interaction_beat"]
    }
```

### Mise à jour après interaction

À chaque message utilisateur traité:
```python
def record_interaction():
    """Record that an interaction occurred at current beat."""
    heartbeat = load_heartbeat()
    heartbeat["last_interaction_at"] = datetime.now().isoformat()
    heartbeat["last_interaction_beat"] = heartbeat["beat"]
    save_heartbeat(heartbeat)
```

## Interprétation par l'agent

### Seuils suggérés

| since_last | Interprétation |
|------------|----------------|
| 0-2 | Conversation active, flow continu |
| 3-12 | Pause courte (~15min - 1h) |
| 13-72 | Session interrompue (~1h - 6h) |
| 73-288 | Nouvelle journée (~6h - 24h) |
| 289+ | Longue absence (>24h) |

*Avec intervalle de 5min par beat*

### Exemple d'utilisation agent

```
<!-- ai_smartness: {"beat": 847, "since_last": 45, "active_count": 43} -->
```

L'agent peut interpréter: "45 beats depuis la dernière interaction = environ 3-4 heures. L'utilisateur revient après une pause significative. Le contexte peut avoir évolué."

## Implémentation

### Fichiers à modifier

1. **daemon/service.py** - Ajouter incrément beat à chaque cycle
2. **hooks/inject.py** - Inclure beat/since_last dans metadata
3. **storage/heartbeat.py** (nouveau) - Gestion du fichier heartbeat

### Nouveau fichier: storage/heartbeat.py

```python
"""Heartbeat storage and management."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

HEARTBEAT_FILE = "heartbeat.json"

def load_heartbeat(ai_path: Path) -> dict:
    """Load heartbeat state from file."""
    filepath = ai_path / HEARTBEAT_FILE
    if not filepath.exists():
        return init_heartbeat(ai_path)

    with open(filepath) as f:
        return json.load(f)

def save_heartbeat(ai_path: Path, heartbeat: dict):
    """Save heartbeat state to file."""
    filepath = ai_path / HEARTBEAT_FILE
    with open(filepath, 'w') as f:
        json.dump(heartbeat, f, indent=2)

def init_heartbeat(ai_path: Path) -> dict:
    """Initialize heartbeat file."""
    heartbeat = {
        "beat": 0,
        "started_at": datetime.now().isoformat(),
        "last_beat_at": datetime.now().isoformat(),
        "last_interaction_at": datetime.now().isoformat(),
        "last_interaction_beat": 0
    }
    save_heartbeat(ai_path, heartbeat)
    return heartbeat

def increment_beat(ai_path: Path) -> int:
    """Increment beat counter. Called by daemon each cycle."""
    heartbeat = load_heartbeat(ai_path)
    heartbeat["beat"] += 1
    heartbeat["last_beat_at"] = datetime.now().isoformat()
    save_heartbeat(ai_path, heartbeat)
    return heartbeat["beat"]

def record_interaction(ai_path: Path):
    """Record that an agent interaction occurred."""
    heartbeat = load_heartbeat(ai_path)
    heartbeat["last_interaction_at"] = datetime.now().isoformat()
    heartbeat["last_interaction_beat"] = heartbeat["beat"]
    save_heartbeat(ai_path, heartbeat)

def get_since_last(ai_path: Path) -> int:
    """Get beats since last interaction."""
    heartbeat = load_heartbeat(ai_path)
    return heartbeat["beat"] - heartbeat["last_interaction_beat"]
```

### Modification daemon/service.py

```python
# Dans la boucle principale du daemon

async def run_cycle(self):
    """Run one daemon cycle."""
    # Existing gossip/decay logic...
    await self.run_gossip()
    await self.run_decay()
    await self.run_pruning()

    # NEW: Increment heartbeat
    from ..storage.heartbeat import increment_beat
    beat = increment_beat(self.ai_path)
    self.logger.debug(f"Heartbeat: {beat}")
```

### Modification hooks/inject.py

```python
# Dans get_memory_context() ou format_metadata()

from ..storage.heartbeat import load_heartbeat, record_interaction

def get_metadata(ai_path: Path, current_thread: dict, active_count: int) -> str:
    """Format metadata for injection."""
    heartbeat = load_heartbeat(ai_path)
    since_last = heartbeat["beat"] - heartbeat["last_interaction_beat"]

    # Record this interaction
    record_interaction(ai_path)

    metadata = {
        "beat": heartbeat["beat"],
        "since_last": since_last,
        "current_thread": current_thread,
        "active_count": active_count
    }

    return f'<!-- ai_smartness: {json.dumps(metadata)} -->'
```

## CLI

### Commande status enrichie

```bash
$ ai status
AI Smartness v4.x
Heartbeat: 847 (running for 4 days)
Since last interaction: 2 beats (~10 min)
Active threads: 45
Bridges: 132
Daemon: running (PID 12345)
```

### Commande heartbeat dédiée

```bash
$ ai heartbeat
Beat: 847
Started: 2026-01-15 08:00:00 (4 days ago)
Last beat: 2026-01-31 11:15:00
Last interaction: 2026-01-31 11:10:00 (beat 845)
Since last: 2 beats
```

## Tests

1. **Test init**: Premier lancement crée heartbeat.json avec beat=0
2. **Test increment**: Daemon incrémente beat à chaque cycle
3. **Test interaction**: record_interaction() met à jour last_interaction_beat
4. **Test since_last**: Calcul correct de beats depuis dernière interaction
5. **Test injection**: Metadata contient beat et since_last
6. **Test persistence**: Beat survit au redémarrage daemon

## Métriques

Logger dans `.ai/daemon.log`:
```
[2026-01-31 11:15:00] HEARTBEAT beat=847 since_interaction=2
```

## Version

- **v4.1.0**: Heartbeat initial
- Dépend de v4.0.0 (Recall Actif) pour le système d'injection enrichi

## Notes de design

### Pourquoi pas le temps humain ?

L'agent a exprimé une préférence pour une abstraction temporelle congruente avec sa nature:
> "Le temps humain (10:45, mardi, janvier) c'est une convention sociale que je comprends mais que je ne 'vis' pas. Un système de beats qui pulse pendant que je suis 'absent' - ça correspond mieux à ma réalité : je n'existe que par intermittence, entre vos messages."

### Relation avec Last active

- **Heartbeat/beats** → Perception temporelle de l'agent (temps système)
- **Last active: X days ago** → Fraîcheur de l'information (temps humain pour évaluer staleness)

Les deux sont complémentaires et servent des buts différents. Voir V4_RECALL_ACTIF.md pour détails.
