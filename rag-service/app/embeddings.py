"""
Embedding service module for IOI AI RAG.

Provides a clean, isolated interface for generating vector embeddings from text.
Supports local sentence-transformers (sentence-transformers/all-MiniLM-L6-v2) by default,
as well as FastEmbed (BAAI/bge-small-en-v1.5), OpenAI, and Ollama providers,
with configurable models and support for switching providers via environment variables.

Never hardcodes API keys or secrets.
"""

from __future__ import annotations

import os
from typing import Sequence

# Lazy-loaded embedding model singleton
_embedding_model = None


def reset_embedding_model() -> None:
    """Reset cached embedding model instance (useful for testing or runtime provider switching)."""
    global _embedding_model
    _embedding_model = None


def get_embedding_model():
    """
    Initialize and cache the embedding model instance based on environment configuration.
    """
    global _embedding_model

    provider = os.environ.get("EMBEDDING_PROVIDER", "fastembed").lower()
    model_name = os.environ.get("EMBEDDING_MODEL")

    # Invalidate cache if provider or model was changed dynamically
    if _embedding_model is not None:
        cached_provider = _embedding_model[0] if isinstance(_embedding_model, tuple) else "fastembed"
        norm_req_provider = "sentence-transformers" if provider in ("sentence-transformers", "sentence_transformers") else provider
        if cached_provider == norm_req_provider:
            return _embedding_model
        _embedding_model = None

    if provider in ("sentence-transformers", "sentence_transformers"):
        if not model_name:
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found,import-untyped]
        _embedding_model = ("sentence-transformers", SentenceTransformer(model_name), model_name)
        return _embedding_model

    elif provider == "fastembed":
        if not model_name:
            model_name = os.environ.get("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
        from fastembed import TextEmbedding  # type: ignore[import-not-found,import-untyped]
        _embedding_model = ("fastembed", TextEmbedding(model_name=model_name), model_name)
        return _embedding_model

    elif provider == "openai":
        # Provider hook for OpenAI if configured
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required when EMBEDDING_PROVIDER=openai")
        try:
            from openai import OpenAI  # type: ignore[import-not-found,import-untyped]
            if not model_name:
                model_name = "text-embedding-3-small"
            _embedding_model = ("openai", OpenAI(api_key=api_key), model_name)
            return _embedding_model
        except ImportError:
            raise ImportError("openai package is required for EMBEDDING_PROVIDER=openai. Run: pip install openai")

    elif provider == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        if not model_name:
            model_name = os.environ.get("OLLAMA_EMBED_MODEL", "all-minilm")
        _embedding_model = ("ollama", base_url, model_name)
        return _embedding_model

    else:
        raise ValueError(
            f"Unsupported EMBEDDING_PROVIDER: '{provider}'. "
            f"Supported: 'sentence-transformers', 'fastembed', 'openai', 'ollama'"
        )


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

    if provider in ("sentence-transformers", "sentence_transformers"):
        _, st_model, _ = model
        raw_embeddings = st_model.encode(
            list(texts),
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return [list(map(float, emb)) for emb in raw_embeddings]

    elif provider == "fastembed":
        # FastEmbed handles generator batching internally
        fe_model = model[1] if isinstance(model, tuple) else model
        raw_embeddings = fe_model.embed(texts, batch_size=batch_size)
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

    elif provider == "ollama":
        import requests
        _, base_url, model_name = model
        embeddings = []
        for text in texts:
            resp = requests.post(
                f"{base_url.rstrip('/')}/api/embeddings",
                json={"model": model_name, "prompt": text},
                timeout=30,
            )
            resp.raise_for_status()
            embeddings.append(list(map(float, resp.json().get("embedding", []))))
        return embeddings

    raise ValueError(f"Unsupported provider: {provider}")
