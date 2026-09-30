"""
IOI AI — Normalized Student Data Model (Python)

Mirrors the TypeScript model in backend/src/models/student.ts.
Used by the RAG service for document processing and future retrieval.

NOTE: No embeddings, vector storage, or LangChain here yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


@dataclass
class SourceMetadata:
    """Tracks where a student record came from."""

    type: Literal["pwioi_public_api", "synthetic"]
    status: Literal["public", "demo"]
    origin: str
    ingested_at: str  # ISO-8601

    @staticmethod
    def public_api(endpoint: str) -> SourceMetadata:
        return SourceMetadata(
            type="pwioi_public_api",
            status="public",
            origin=endpoint,
            ingested_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def synthetic(label: str = "synthetic-generator") -> SourceMetadata:
        return SourceMetadata(
            type="synthetic",
            status="demo",
            origin=label,
            ingested_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class StudentProject:
    """A project associated with a student (synthetic/demo only)."""

    title: str
    description: str | None = None
    url: str | None = None


@dataclass
class PublicLinks:
    """Public web links for a student profile."""

    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None


@dataclass
class Student:
    """
    Normalized student record.

    Fields populated from the PW IOI public API:
        id, name, gender, address (currently null), campus*, batch*, school*
        (* derived from request context)

    Fields only populated for synthetic/demo records:
        skills, projects, interests, public_links
    """

    id: str
    name: str
    campus: str
    batch: str
    gender: Literal["MALE", "FEMALE"]
    source: SourceMetadata
    school: str = "SOT"
    address: str | None = None
    skills: list[str] = field(default_factory=list)
    projects: list[StudentProject] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    public_links: PublicLinks = field(default_factory=PublicLinks)

    @staticmethod
    def from_public_api(
        raw: dict,
        campus: str,
        batch: str,
        api_endpoint: str,
    ) -> Student:
        """Create a Student from raw PW IOI API response data."""
        return Student(
            id=raw["id"],
            name=raw["name"],
            gender=raw["gender"],
            address=raw.get("address"),
            campus=campus,
            batch=batch,
            source=SourceMetadata.public_api(api_endpoint),
        )


# ---- Future RAG document representation (placeholder) ---------------------

@dataclass
class StudentDocument:
    """
    Represents a student as a text document for future RAG indexing.

    This is a placeholder — embedding generation, chunking, and vector
    storage will be implemented in a later phase.
    """

    student_id: str
    content: str  # Flattened text representation of the student
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def from_student(student: Student) -> StudentDocument:
        """Convert a Student into a plain-text document for future RAG use."""
        parts = [
            f"Name: {student.name}",
            f"Campus: {student.campus}",
            f"Batch: {student.batch}",
            f"Gender: {student.gender}",
            f"School: {student.school}",
        ]

        if student.address:
            parts.append(f"Address: {student.address}")
        if student.skills:
            parts.append(f"Skills: {', '.join(student.skills)}")
        if student.interests:
            parts.append(f"Interests: {', '.join(student.interests)}")
        for proj in student.projects:
            line = f"Project: {proj.title}"
            if proj.description:
                line += f" — {proj.description}"
            parts.append(line)

        return StudentDocument(
            student_id=student.id,
            content="\n".join(parts),
            metadata={
                "campus": student.campus,
                "batch": student.batch,
                "school": student.school,
                "source_type": student.source.type,
                "source_status": student.source.status,
            },
        )
