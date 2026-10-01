"""
Local vector store module for IOI AI.

Uses ChromaDB as a lightweight, embedded, file-based vector database.
Provides modular functions for index creation, loading, and cosine similarity search.
Completely local, self-contained, and free — no cloud services required.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Sequence

import chromadb
from chromadb.api.models.Collection import Collection

# Default persistent directory for ChromaDB: data/vectorstore
DEFAULT_VECTOR_STORE_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "vectorstore"
)
DEFAULT_COLLECTION_NAME = "students"


def get_vector_store_dir() -> Path:
    """Return the configured or default directory for vector store persistence."""
    custom_path = os.environ.get("VECTOR_STORE_PATH")
    if custom_path:
        p = Path(custom_path)
        if not p.is_absolute():
            if p.exists():
                return p.resolve()
            candidate_service = Path(__file__).resolve().parents[1] / p
            if candidate_service.exists():
                return candidate_service.resolve()
            candidate_workspace = Path(__file__).resolve().parents[2] / p
            if candidate_workspace.exists():
                return candidate_workspace.resolve()
        return p.resolve()

    provider = os.environ.get("EMBEDDING_PROVIDER", "fastembed").lower()
    if provider in ("sentence-transformers", "sentence_transformers"):
        service_hf_dir = Path(__file__).resolve().parents[1] / "data" / "vectorstore_hf"
        if service_hf_dir.exists():
            return service_hf_dir
        root_hf_dir = Path(__file__).resolve().parents[2] / "data" / "vectorstore_hf"
        if root_hf_dir.exists():
            return root_hf_dir

    return DEFAULT_VECTOR_STORE_DIR


def get_client(persist_dir: Path | str | None = None) -> chromadb.PersistentClient:
    """Get a ChromaDB PersistentClient instance."""
    path = Path(persist_dir) if persist_dir else get_vector_store_dir()
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def get_or_create_collection(
    persist_dir: Path | str | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Collection:
    """
    Get or create a ChromaDB collection configured for cosine distance.
    """
    client = get_client(persist_dir)
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def load_index(
    persist_dir: Path | str | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Collection:
    """
    Load an existing ChromaDB collection index.
    """
    client = get_client(persist_dir)
    return client.get_collection(name=collection_name)


def create_or_replace_index(
    records: Sequence[dict[str, Any]],
    persist_dir: Path | str | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    batch_size: int = 100,
) -> int:
    """
    Build or replace the vector index from a list of embedded student records.

    Each record must have:
      - document_id (str)
      - embedding (list[float])
      - content (str)
      - metadata (dict)

    Args:
        records: List of document dicts.
        persist_dir: Optional path for storage directory.
        collection_name: Collection name in ChromaDB.
        batch_size: Number of records to add per batch.

    Returns:
        Total number of documents indexed.
    """
    client = get_client(persist_dir)

    # Delete collection if it already exists to guarantee clean rebuild
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    total = len(records)
    if total == 0:
        return 0

    for i in range(0, total, batch_size):
        chunk = records[i : i + batch_size]
        ids = [str(r["document_id"]) for r in chunk]
        embeddings = [r["embedding"] for r in chunk]
        documents = [str(r["content"]) for r in chunk]
        metadatas = [r["metadata"] for r in chunk]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    return collection.count()


def similarity_search(
    query_text: str | None = None,
    query_embedding: list[float] | None = None,
    top_k: int = 5,
    where: dict[str, Any] | None = None,
    persist_dir: Path | str | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> list[dict[str, Any]]:
    """
    Perform cosine similarity search against the vector index.

    Either query_embedding or query_text must be provided.
    If query_text is provided without query_embedding, the query is embedded
    using the app.embeddings module.

    Args:
        query_text: Plain text search query.
        query_embedding: Precomputed 384-dimensional vector.
        top_k: Number of most similar results to return.
        where: Optional ChromaDB metadata filter.
        persist_dir: Optional path to vector store directory.
        collection_name: Collection name to query.

    Returns:
        List of result dictionaries containing document_id, content, metadata,
        cosine distance, and similarity score.
    """
    if query_embedding is None:
        if not query_text:
            raise ValueError("Either query_embedding or query_text must be provided")
        from app.embeddings import embed_text
        query_embedding = embed_text(query_text)

    collection = load_index(persist_dir, collection_name)

    query_params: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
    }
    if where:
        query_params["where"] = where

    results = collection.query(**query_params)

    hits: list[dict[str, Any]] = []
    if not results or not results["ids"] or not results["ids"][0]:
        return hits

    ids = results["ids"][0]
    docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
    metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
    distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

    for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
        # With cosine distance: similarity = 1.0 - distance
        similarity = 1.0 - dist
        hits.append({
            "document_id": doc_id,
            "content": doc,
            "metadata": meta,
            "distance": round(dist, 4),
            "similarity_score": round(similarity, 4),
        })

    return hits
