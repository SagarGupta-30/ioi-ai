"""
Embedding service module for IOI AI RAG.

Provides a clean, isolated interface for generating vector embeddings from text.
Supports local fast embeddings via FastEmbed (BAAI/bge-small-en-v1.5) by default,
with configurable models and support for switching providers via environment variables.

Never hardcodes API keys or secrets.
"""

from __future__ import annotations

import os
from typing import Sequence

# Lazy-loaded embedding model singleton
_embedding_model = None


def get_embedding_model():
    """
    Initialize and cache the embedding model instance based on environment configuration.
    """
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    provider = os.environ.get("EMBEDDING_PROVIDER", "fastembed").lower()
    model_name = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

    if provider == "fastembed":
        from fastembed import TextEmbedding
        _embedding_model = TextEmbedding(model_name=model_name)
        return _embedding_model
    elif provider == "openai":
        # Provider hook for OpenAI if configured
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required when EMBEDDING_PROVIDER=openai")
        try:
            from openai import OpenAI
            _embedding_model = ("openai", OpenAI(api_key=api_key), model_name)
            return _embedding_model
        except ImportError:
            raise ImportError("openai package is required for EMBEDDING_PROVIDER=openai. Run: pip install openai")
    else:
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: '{provider}'. Supported: 'fastembed', 'openai'")


def embed_text(text: str) -> list[float]:
    """
    Generate an embedding vector for a single text string.

    Args:
        text: Input string to embed.

    Returns:
        List of floats representing the embedding vector.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str for text, got {type(text).__name__}")

    results = embed_documents([text], batch_size=1)
    if not results:
        raise RuntimeError("Embedding generation produced no results")
    return results[0]


def embed_documents(texts: Sequence[str], batch_size: int = 64) -> list[list[float]]:
    """
    Generate embedding vectors for a sequence of text strings in batches.

    Args:
        texts: Sequence of strings to embed.
        batch_size: Batch size for model inference.

    Returns:
        List of embedding vectors, one for each input text.
    """
    if not texts:
        return []

    for i, t in enumerate(texts):
        if not isinstance(t, str):
            raise TypeError(f"Item at index {i} is not a string (type: {type(t).__name__})")

    model = get_embedding_model()

    provider = os.environ.get("EMBEDDING_PROVIDER", "fastembed").lower()

    if provider == "fastembed":
        # FastEmbed handles generator batching internally
        raw_embeddings = model.embed(texts, batch_size=batch_size)
        return [list(map(float, emb)) for emb in raw_embeddings]

    elif provider == "openai":
        _, client, model_name = model
        embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = list(texts[i : i + batch_size])
            response = client.embeddings.create(input=chunk, model=model_name)
            for item in response.data:
                embeddings.append(item.embedding)
        return embeddings

    raise ValueError(f"Unsupported provider: {provider}")
