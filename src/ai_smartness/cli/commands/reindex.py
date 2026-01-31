"""Reindex command - Recalculate all thread embeddings.

Use this command after:
- Upgrading the embedding algorithm
- Fixing embedding compatibility issues
- Migrating from old versions
- Changing embedding model
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def get_package_root() -> Path:
    """Get the ai_smartness package root."""
    return Path(__file__).parent.parent.parent


def run_reindex(
    ai_path: Path,
    verbose: bool = False,
    reset_weights: bool = False
) -> int:
    """
    Recalculate embeddings for all threads.

    Args:
        ai_path: Path to .ai directory
        verbose: Show detailed progress
        reset_weights: Reset all weights to 1.0

    Returns:
        Exit code
    """
    # Add package to path
    package_root = get_package_root()
    parent_path = str(package_root.parent)
    if parent_path not in sys.path:
        sys.path.insert(0, parent_path)

    try:
        from ai_smartness.processing.embeddings import EmbeddingManager
    except ImportError as e:
        print(f"ERROR: Could not import EmbeddingManager: {e}")
        return 1

    threads_dir = ai_path / "db" / "threads"
    if not threads_dir.exists():
        print("No threads directory found.")
        return 0

    em = EmbeddingManager()
    print(f"Embedding Manager: {type(em).__name__}")
    print(f"Using Transformers: {em.is_using_transformers}")
    if reset_weights:
        print("Weight reset: ENABLED (all weights will be set to 1.0)")
    print()

    # Find all thread files
    thread_files = list(threads_dir.glob("thread_*.json"))
    total = len(thread_files)

    if total == 0:
        print("No threads found.")
        return 0

    print(f"Recalculating embeddings for {total} threads...")
    print()

    count = 0
    errors = 0
    now = datetime.now().isoformat()

    for i, f in enumerate(thread_files):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            thread_id = data.get("id", f.stem)[:20]

            # Build text from all relevant fields
            text_parts = []

            # Title is most important
            if data.get("title"):
                text_parts.append(data["title"])

            # Summary captures the essence
            if data.get("summary"):
                text_parts.append(data["summary"])

            # Topics are key semantic markers
            if data.get("topics"):
                text_parts.extend(data["topics"])

            # Recent messages (last 5, truncated)
            messages = data.get("messages", [])
            for msg in messages[-5:]:
                content = msg.get("content", "")[:300]
                if content:
                    text_parts.append(content)

            combined_text = " ".join(text_parts)

            if not combined_text.strip():
                if verbose:
                    print(f"  [{i+1}/{total}] {thread_id}... SKIP (no content)")
                continue

            # Recalculate embedding
            new_embedding = em.embed(combined_text)
            data["embedding"] = new_embedding

            # Optionally reset weight
            if reset_weights:
                data["weight"] = 1.0
                data["last_active"] = now

            # Save
            f.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            count += 1

            if verbose:
                title = data.get('title', '')[:35]
                status = data.get('status', 'unknown')
                print(f"  [{i+1}/{total}] {title}... OK ({status})")
            elif (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{total}")

        except json.JSONDecodeError as e:
            print(f"  ERROR parsing {f.name}: {e}")
            errors += 1
        except Exception as e:
            print(f"  ERROR processing {f.name}: {e}")
            errors += 1

    print()
    print(f"Done! Recalculated {count} embeddings.")
    if errors > 0:
        print(f"Errors: {errors}")

    # Check for daemon
    pid_file = ai_path / "processor.pid"
    if pid_file.exists():
        print()
        print("NOTE: Restart the daemon to use new embeddings:")
        print("  ai daemon stop && ai daemon start")
        print("  or: kill $(cat .ai/processor.pid)")

    return 0 if errors == 0 else 1
