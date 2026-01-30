"""Reindex command - Recalculate all thread embeddings.

Use this command after:
- Upgrading the embedding algorithm
- Fixing embedding compatibility issues
- Migrating from old versions
"""

import json
from pathlib import Path
from typing import Optional


def run_reindex(ai_path: Path, verbose: bool = False) -> int:
    """
    Recalculate embeddings for all threads.

    Args:
        ai_path: Path to .ai directory
        verbose: Show detailed progress

    Returns:
        Exit code
    """
    import sys

    # Add package to path
    package_dir = ai_path.parent
    if str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))

    try:
        from ai_smartness_v2.processing.embeddings import EmbeddingManager
    except ImportError:
        print("ERROR: Could not import EmbeddingManager")
        return 1

    threads_dir = ai_path / "db" / "threads"
    if not threads_dir.exists():
        print("No threads directory found.")
        return 0

    em = EmbeddingManager()
    print(f"Using embedding manager: {type(em).__name__}")
    print(f"Transformers: {em.is_using_transformers}")
    print()

    thread_files = list(threads_dir.glob("thread_*.json"))
    total = len(thread_files)

    print(f"Recalculating embeddings for {total} threads...")

    count = 0
    for i, f in enumerate(thread_files):
        try:
            data = json.loads(f.read_text())

            # Build text from title + topics + messages
            text_parts = [data.get("title", "")]
            text_parts.extend(data.get("topics", []))
            for msg in data.get("messages", [])[-5:]:
                text_parts.append(msg.get("content", "")[:200])

            combined_text = " ".join(text_parts)

            # Recalculate embedding
            new_embedding = em.embed(combined_text)
            data["embedding"] = new_embedding

            # Save
            f.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            count += 1

            if verbose:
                print(f"  [{i+1}/{total}] {data.get('title', '')[:40]}")
            elif (i + 1) % 20 == 0:
                print(f"  Progress: {i+1}/{total}")

        except Exception as e:
            print(f"  ERROR processing {f.name}: {e}")

    print(f"\nDone! Recalculated {count} embeddings.")
    print("\nNOTE: Restart the daemon to use new embeddings:")
    print("  kill $(cat .ai/processor.pid)")

    return 0
