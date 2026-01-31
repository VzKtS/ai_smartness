"""Search command - Semantic search across threads."""

import json
from pathlib import Path
from typing import List, Tuple

# Try to import embeddings, fall back to keyword search
try:
    from ...processing.embeddings import get_embedding_manager
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False


def keyword_search(ai_path: Path, query: str, limit: int) -> List[Tuple[float, dict]]:
    """
    Simple keyword-based search fallback.

    Args:
        ai_path: Path to .ai directory
        query: Search query
        limit: Maximum results

    Returns:
        List of (score, thread_data) tuples
    """
    threads_path = ai_path / "db" / "threads"
    results = []

    if not threads_path.exists():
        return results

    query_words = set(query.lower().split())

    for thread_file in threads_path.glob("thread_*.json"):
        try:
            data = json.loads(thread_file.read_text())

            # Build searchable text
            title = data.get("title", "").lower()
            topics = " ".join(data.get("topics", [])).lower()
            summary = data.get("summary", "").lower()

            # First message content
            messages = data.get("messages", [])
            first_content = messages[0].get("content", "")[:500].lower() if messages else ""

            searchable = f"{title} {topics} {summary} {first_content}"

            # Count matching words
            matches = sum(1 for word in query_words if word in searchable)
            if matches > 0:
                score = matches / len(query_words)
                results.append((score, data))

        except Exception:
            pass

    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:limit]


def semantic_search(ai_path: Path, query: str, limit: int) -> List[Tuple[float, dict]]:
    """
    Embedding-based semantic search.

    Args:
        ai_path: Path to .ai directory
        query: Search query
        limit: Maximum results

    Returns:
        List of (score, thread_data) tuples
    """
    if not HAS_EMBEDDINGS:
        return keyword_search(ai_path, query, limit)

    threads_path = ai_path / "db" / "threads"
    results = []

    if not threads_path.exists():
        return results

    try:
        embeddings = get_embedding_manager()
        query_embedding = embeddings.embed(query)
    except Exception:
        return keyword_search(ai_path, query, limit)

    for thread_file in threads_path.glob("thread_*.json"):
        try:
            data = json.loads(thread_file.read_text())

            # Check if thread has embedding
            thread_embedding = data.get("embedding")
            if thread_embedding:
                similarity = embeddings.similarity(query_embedding, thread_embedding)
                results.append((similarity, data))
            else:
                # Fall back to keyword match for this thread
                title = data.get("title", "").lower()
                if any(word in title for word in query.lower().split()):
                    results.append((0.5, data))

        except Exception:
            pass

    # Sort by similarity descending
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:limit]


def run_search(ai_path: Path, query: str, limit: int) -> int:
    """
    Search threads.

    Args:
        ai_path: Path to .ai directory
        query: Search query
        limit: Maximum results

    Returns:
        Exit code
    """
    print(f"\nSearching for: \"{query}\"")
    print()

    # Try semantic search, fall back to keyword
    if HAS_EMBEDDINGS:
        results = semantic_search(ai_path, query, limit)
        search_type = "semantic"
    else:
        results = keyword_search(ai_path, query, limit)
        search_type = "keyword"

    if not results:
        print("No matching threads found.")
        return 0

    print(f"Results ({search_type} search):")
    print("-" * 60)

    for score, thread in results:
        thread_id = thread.get("id", "")[:12]
        title = thread.get("title", "Untitled")[:45]
        status = thread.get("status", "active")
        topics = ", ".join(thread.get("topics", [])[:3])

        print(f"  [{score:.2f}] {title}")
        print(f"          ID: {thread_id}.. | Status: {status}")
        if topics:
            print(f"          Topics: {topics}")
        print()

    return 0
