"""
Document builder: converts a MongoDB student record into a RAG document.

Rules:
- Never fabricate missing fields.
- Empty skills/projects/interests become "Not available".
- Preserve source provenance.
- Distinguish synthetic/demo from public records.
"""

from __future__ import annotations

from .rag_models import RAGDocument, RAGDocumentMetadata


def _format_list(items: list, label: str) -> str:
    """Format a list field, showing 'Not available' if empty."""
    if items:
        return f"{label}: {', '.join(str(i) for i in items)}"
    return f"{label}: Not available"


def _format_projects(projects: list[dict]) -> str:
    """Format projects list into readable text."""
    if not projects:
        return "Projects: Not available"

    lines = ["Projects:"]
    for p in projects:
        title = p.get("title", "Untitled")
        desc = p.get("description")
        line = f"  - {title}"
        if desc:
            line += f": {desc}"
        url = p.get("url")
        if url:
            line += f" ({url})"
        lines.append(line)
    return "\n".join(lines)


def _format_source(source: dict) -> str:
    """Format source provenance into readable text."""
    source_type = source.get("type", "unknown")
    if source_type == "pwioi_public_api":
        return "Source: PW IOI public API"
    elif source_type == "synthetic":
        return "Source: Synthetic / demo data"
    return f"Source: {source_type}"


def build_document(record: dict) -> RAGDocument | None:
    """
    Convert one MongoDB student record into a RAGDocument.

    The record uses Mongoose field names (studentId, not id).
    Returns None if the record is missing required fields.
    """
    student_id = record.get("studentId")
    name = record.get("name")
    campus = record.get("campus", "Unknown")
    batch = record.get("batch", "Unknown")
    gender = record.get("gender", "Unknown")
    school = record.get("school", "SOT")
    source = record.get("source", {})

    if not student_id or not name:
        return None

    # Build content text
    parts = [
        f"Student: {name}",
        f"School: {school}",
        f"Campus: {campus}",
        f"Batch: {batch}",
        f"Gender: {gender}",
    ]

    address = record.get("address")
    if address:
        parts.append(f"Address: {address}")

    parts.append(_format_list(record.get("skills", []), "Skills"))
    parts.append(_format_projects(record.get("projects", [])))
    parts.append(_format_list(record.get("interests", []), "Interests"))

    # Public links
    links = record.get("publicLinks", {})
    link_items = []
    if links.get("linkedin"):
        link_items.append(f"LinkedIn: {links['linkedin']}")
    if links.get("github"):
        link_items.append(f"GitHub: {links['github']}")
    if links.get("portfolio"):
        link_items.append(f"Portfolio: {links['portfolio']}")
    if link_items:
        parts.append("Links: " + ", ".join(link_items))

    parts.append(_format_source(source))

    content = "\n".join(parts)

    # Build metadata
    metadata = RAGDocumentMetadata(
        student_id=student_id,
        name=name,
        campus=campus,
        batch=batch,
        gender=gender,
        school=school,
        source_type=source.get("type", "unknown"),
        source_status=source.get("status", "unknown"),
        source_origin=source.get("origin", "unknown"),
    )

    return RAGDocument(
        document_id=student_id,
        content=content,
        metadata=metadata,
    )
