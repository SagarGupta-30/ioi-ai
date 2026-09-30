"""
Student Retriever Module for IOI AI.

Handles semantic search and filtered retrieval of student records from the local
ChromaDB vector store. Uses FastEmbed for query embedding, supporting both pure
semantic similarity and structured metadata filtering.

Zero external APIs or LLMs used here — 100% local, offline, and free.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from app.embeddings import embed_text
from app.vector_store import get_vector_store_dir, similarity_search

# Configurable retrieval settings (environment variables with robust defaults)
DEFAULT_TOP_K = int(os.environ.get("TOP_K_DEFAULT", "5"))
MAX_TOP_K = int(os.environ.get("TOP_K_MAX", "50"))
DEFAULT_SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.58"))


@dataclass
class RetrievalResult:
    """Represents a single retrieved document with similarity score and metadata."""

    document_id: str
    content: str
    metadata: dict[str, Any]
    similarity_score: float
    distance: float

    @property
    def name(self) -> str:
        return self.metadata.get("name", "Unknown")

    @property
    def campus(self) -> str:
        return self.metadata.get("campus", "Unknown")

    @property
    def batch(self) -> str:
        return str(self.metadata.get("batch", "Unknown"))

    @property
    def gender(self) -> str:
        return self.metadata.get("gender", "Unknown")

    @property
    def school(self) -> str:
        return self.metadata.get("school", "Unknown")

    @property
    def source_type(self) -> str:
        return self.metadata.get("source_type", "unknown")

    @property
    def source_status(self) -> str:
        return self.metadata.get("source_status", "unknown")

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "content": self.content,
            "metadata": self.metadata,
            "similarity_score": self.similarity_score,
            "distance": self.distance,
        }


def build_metadata_filter(
    campus: str | None = None,
    batch: str | int | None = None,
    gender: str | None = None,
    school: str | None = None,
) -> dict[str, Any] | None:
    """
    Construct a ChromaDB metadata filter dictionary.

    Normalizes inputs (e.g. gender 'male' -> 'MALE', campus 'bengaluru' -> 'Bengaluru').
    Returns None if no filters are applied.
    """
    clauses: list[dict[str, Any]] = []

    if campus:
        # Standardize campus casing (Bengaluru, Pune, Noida, Lucknow)
        normalized_campus = campus.strip().title()
        clauses.append({"campus": normalized_campus})

    if batch is not None:
        clauses.append({"batch": str(batch).strip()})

    if gender:
        normalized_gender = gender.strip().upper()
        clauses.append({"gender": normalized_gender})

    if school:
        clauses.append({"school": school.strip().upper()})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def detect_query_constraints(query: str) -> dict[str, Any]:
    """
    Extract structured metadata constraints from natural-language query if present.
    Detects campus, batch ('batch 24', etc.), and gender ('male', 'female').
    """
    import re

    detected: dict[str, Any] = {}
    lower = query.lower()

    # 1. Detect campus
    for campus_name in ["Bengaluru", "Pune", "Noida", "Lucknow"]:
        if campus_name.lower() in lower:
            detected["campus"] = campus_name
            break

    # 2. Detect batch (e.g., 'batch 24', 'batch 26')
    batch_match = re.search(r"\bbatch\s*(\d{2})\b", lower)
    if batch_match:
        detected["batch"] = batch_match.group(1)

    # 3. Detect gender
    if re.search(r"\bfemale\b", lower) or re.search(r"\bgirls?\b", lower) or re.search(r"\bwomen\b", lower):
        detected["gender"] = "FEMALE"
    elif re.search(r"\bmale\b", lower) or re.search(r"\bboys?\b", lower) or re.search(r"\bmen\b", lower):
        detected["gender"] = "MALE"

    return detected


class StudentRetriever:
    """
    Retrieval client that wraps embedding generation and vector store search.
    """

    def __init__(
        self,
        persist_dir: Path | str | None = None,
        collection_name: str = "students",
    ):
        self.persist_dir = Path(persist_dir) if persist_dir else get_vector_store_dir()
        self.collection_name = collection_name

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        campus: str | None = None,
        batch: str | int | None = None,
        gender: str | None = None,
        school: str | None = None,
        where: dict[str, Any] | None = None,
        similarity_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve the top-K most similar student documents for a natural-language query.

        Args:
            query: Natural-language search string.
            top_k: Number of ranked results to return (default: TOP_K_DEFAULT, max: TOP_K_MAX).
            campus: Optional filter by campus name ('Bengaluru', 'Pune', etc.).
            batch: Optional filter by batch ('24', '25', '26', etc.).
            gender: Optional filter by gender ('MALE', 'FEMALE').
            school: Optional filter by school ('SOT').
            where: Optional explicit ChromaDB filter override.
            similarity_threshold: Optional cosine similarity cutoff.

        Returns:
            List of RetrievalResult objects ordered by descending similarity.
        """
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty")

        cleaned_query = query.strip()
        effective_top_k = min(top_k or DEFAULT_TOP_K, MAX_TOP_K)

        # 1. Embed query using existing FastEmbed embedding model
        query_embedding = embed_text(cleaned_query)

        # 2. Build metadata filter if provided or detect from query
        explicit_filter = where if where is not None else build_metadata_filter(
            campus=campus,
            batch=batch,
            gender=gender,
            school=school,
        )

        filter_to_use = explicit_filter
        if filter_to_use is None:
            auto_constraints = detect_query_constraints(cleaned_query)
            if auto_constraints:
                filter_to_use = build_metadata_filter(**auto_constraints)

        # 3. Query ChromaDB vector index with filter
        raw_hits = similarity_search(
            query_embedding=query_embedding,
            top_k=effective_top_k,
            where=filter_to_use,
            persist_dir=self.persist_dir,
            collection_name=self.collection_name,
        )

        # Fallback to unfiltered search if filter was auto-applied and returned nothing
        if not raw_hits and filter_to_use is not None and explicit_filter is None:
            raw_hits = similarity_search(
                query_embedding=query_embedding,
                top_k=effective_top_k,
                where=None,
                persist_dir=self.persist_dir,
                collection_name=self.collection_name,
            )

        # 4. Wrap hits in RetrievalResult
        results = [
            RetrievalResult(
                document_id=hit["document_id"],
                content=hit["content"],
                metadata=hit["metadata"],
                similarity_score=hit["similarity_score"],
                distance=hit["distance"],
            )
            for hit in raw_hits
        ]

        # 5. Apply threshold filter if explicitly requested
        if similarity_threshold is not None and similarity_threshold > 0:
            results = [r for r in results if r.similarity_score >= similarity_threshold]

        return results

    def retrieve_with_status(
        self,
        query: str,
        top_k: int | None = None,
        campus: str | None = None,
        batch: str | int | None = None,
        gender: str | None = None,
        school: str | None = None,
        where: dict[str, Any] | None = None,
        similarity_threshold: float | None = None,
    ) -> tuple[list[RetrievalResult], str]:
        """
        Retrieve students and report explicit retrieval status:
        - 'sufficient': At least one document matches and meets the similarity threshold.
        - 'insufficient_results': Documents were found in ChromaDB, but all similarity scores are below threshold.
        - 'no_results': Zero documents found matching the filter/query in ChromaDB.
        """
        effective_top_k = min(top_k or DEFAULT_TOP_K, MAX_TOP_K)
        all_results = self.retrieve(
            query=query,
            top_k=effective_top_k,
            campus=campus,
            batch=batch,
            gender=gender,
            school=school,
            where=where,
            similarity_threshold=0.0,
        )

        if not all_results:
            return [], "no_results"

        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else DEFAULT_SIMILARITY_THRESHOLD
        )
        passing_results = [r for r in all_results if r.similarity_score >= threshold]

        if not passing_results:
            return [], "insufficient_results"

        return passing_results, "sufficient"


# Singleton default retriever instance
_default_retriever: StudentRetriever | None = None


def get_retriever() -> StudentRetriever:
    """Get or create the singleton StudentRetriever."""
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = StudentRetriever()
    return _default_retriever


def retrieve_students(
    query: str,
    top_k: int | None = None,
    campus: str | None = None,
    batch: str | int | None = None,
    gender: str | None = None,
    school: str | None = None,
    where: dict[str, Any] | None = None,
    similarity_threshold: float | None = None,
) -> list[RetrievalResult]:
    """
    Convenience function for retrieving students using the default retriever.
    """
    retriever = get_retriever()
    return retriever.retrieve(
        query=query,
        top_k=top_k,
        campus=campus,
        batch=batch,
        gender=gender,
        school=school,
        where=where,
        similarity_threshold=similarity_threshold,
    )


def retrieve_with_status(
    query: str,
    top_k: int | None = None,
    campus: str | None = None,
    batch: str | int | None = None,
    gender: str | None = None,
    school: str | None = None,
    where: dict[str, Any] | None = None,
    similarity_threshold: float | None = None,
) -> tuple[list[RetrievalResult], str]:
    """
    Convenience function returning (results, status).
    """
    retriever = get_retriever()
    return retriever.retrieve_with_status(
        query=query,
        top_k=top_k,
        campus=campus,
        batch=batch,
        gender=gender,
        school=school,
        where=where,
        similarity_threshold=similarity_threshold,
    )


def format_context(results: Sequence[RetrievalResult]) -> str:
    """
    Format a list of retrieval results into a clean context string for future LLM consumption.
    """
    if not results:
        return "No relevant student records found."

    blocks = []
    for idx, r in enumerate(results, start=1):
        block = (
            f"[Student Record {idx}]\n"
            f"{r.content.strip()}"
        )
        blocks.append(block)

    return "\n\n---\n\n".join(blocks)
