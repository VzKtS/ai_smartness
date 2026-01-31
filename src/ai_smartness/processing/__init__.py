"""Processing layer for AI Smartness."""

from .extractor import LLMExtractor, Extraction, extract_title_from_content
from .embeddings import EmbeddingManager, get_embedding_manager

__all__ = [
    "LLMExtractor",
    "Extraction",
    "extract_title_from_content",
    "EmbeddingManager",
    "get_embedding_manager"
]
