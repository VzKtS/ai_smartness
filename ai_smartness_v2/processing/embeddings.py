"""
Embeddings Manager - Vector embeddings for semantic similarity.

Uses sentence-transformers locally (free, offline, fast).
Falls back to simple TF-IDF if sentence-transformers not installed.
"""

import json
import math
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from collections import Counter
import re


class EmbeddingManager:
    """
    Manages text embeddings for semantic similarity.

    Primary: sentence-transformers (if installed)
    Fallback: TF-IDF based embeddings
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding manager.

        Args:
            model_name: Sentence-transformers model name
        """
        self.model_name = model_name
        self._model = None
        self._use_transformers = False

        # Try to load sentence-transformers
        self._init_model()

    def _init_model(self):
        """Initialize the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._use_transformers = True
        except ImportError:
            # sentence-transformers not installed, use fallback
            self._use_transformers = False
            self._idf_cache: Dict[str, float] = {}
            self._document_count = 0

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (list of floats)
        """
        if not text:
            return [0.0] * 384  # Return zero vector

        if self._use_transformers:
            return self._embed_transformers(text)
        else:
            return self._embed_tfidf(text)

    def _embed_transformers(self, text: str) -> List[float]:
        """Embed using sentence-transformers."""
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def _embed_tfidf(self, text: str) -> List[float]:
        """
        Embed using TF-IDF (fallback).

        Creates a sparse-ish vector based on term frequencies.
        """
        # Tokenize
        words = self._tokenize(text)
        if not words:
            return [0.0] * 384

        # Calculate TF (term frequency)
        tf = Counter(words)
        total = len(words)

        # Create embedding from word hashes
        # Use a fixed-size vector (384 to match MiniLM)
        embedding = [0.0] * 384

        for word, count in tf.items():
            # Hash word to get index
            idx = hash(word) % 384
            # TF value (normalized)
            value = count / total
            # Add to embedding (may accumulate if hash collision)
            embedding[idx] += value

        # Normalize
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Lowercase and split
        text = text.lower()
        # Keep alphanumeric and common word boundaries
        words = re.findall(r'\b[a-z][a-z0-9_]*\b', text)
        # Filter stopwords (basic set)
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et',
            'ou', 'que', 'qui', 'dans', 'pour', 'avec', 'sur', 'par'
        }
        return [w for w in words if w not in stopwords and len(w) > 2]

    def similarity(self, a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            a: First embedding vector
            b: Second embedding vector

        Returns:
            Cosine similarity (0 to 1)
        """
        if not a or not b or len(a) != len(b):
            return 0.0

        # Dot product
        dot = sum(x * y for x, y in zip(a, b))

        # Magnitudes
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot / (mag_a * mag_b)

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts (more efficient for transformers).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        if self._use_transformers:
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return [e.tolist() for e in embeddings]
        else:
            return [self._embed_tfidf(text) for text in texts]

    def find_most_similar(
        self,
        query_embedding: List[float],
        candidates: List[Tuple[str, List[float]]],
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        """
        Find most similar items to query.

        Args:
            query_embedding: Query embedding vector
            candidates: List of (id, embedding) tuples
            top_k: Number of results to return
            threshold: Minimum similarity threshold

        Returns:
            List of (id, similarity) tuples, sorted by similarity
        """
        results = []

        for item_id, embedding in candidates:
            sim = self.similarity(query_embedding, embedding)
            if sim >= threshold:
                results.append((item_id, sim))

        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    @property
    def is_using_transformers(self) -> bool:
        """Check if using sentence-transformers or fallback."""
        return self._use_transformers

    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return 384  # MiniLM dimension


# Singleton instance
_embedding_manager: Optional[EmbeddingManager] = None


def get_embedding_manager() -> EmbeddingManager:
    """Get or create the global embedding manager."""
    global _embedding_manager
    if _embedding_manager is None:
        _embedding_manager = EmbeddingManager()
    return _embedding_manager
