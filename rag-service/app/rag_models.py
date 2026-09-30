"""
RAG Document model for IOI AI.

Represents a student record as a structured document ready for
future embedding and retrieval. No embeddings or vector storage here yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RAGDocumentMetadata:
    """Structured metadata preserved alongside the document content."""

    student_id: str
    name: str
    campus: str
    batch: str
    gender: str
    school: str
    source_type: str    # "pwioi_public_api" or "synthetic"
    source_status: str  # "public" or "demo"
    source_origin: str  # API endpoint URL or generator label


@dataclass
class RAGDocument:
    """
    A single RAG document derived from a student record.

    - document_id: unique identifier (same as the student's ID)
    - content: human-readable text representation of the student
    - metadata: structured fields for filtering and provenance
    """

    document_id: str
    content: str
    metadata: RAGDocumentMetadata

    def to_dict(self) -> dict:
        """Serialize to a plain dict for JSON output."""
        return {
            "document_id": self.document_id,
            "content": self.content,
            "metadata": {
                "student_id": self.metadata.student_id,
                "name": self.metadata.name,
                "campus": self.metadata.campus,
                "batch": self.metadata.batch,
                "gender": self.metadata.gender,
                "school": self.metadata.school,
                "source_type": self.metadata.source_type,
                "source_status": self.metadata.source_status,
                "source_origin": self.metadata.source_origin,
            },
        }
