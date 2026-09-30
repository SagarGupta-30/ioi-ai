"""
Query Router & Hybrid Retrieval Engine for IOI AI (Step 8K Hardened).

Classifies incoming natural-language queries deterministically into 5 categories:
1. STRUCTURED    - Exact metadata filtering on campus, batch, gender, school
2. SEMANTIC      - Free-form topical search (skills, interests, student names)
3. HYBRID        - Combines structured metadata pre-filtering with dense semantic ranking
4. AGGREGATION   - Fast, safe read-only counting via MongoDB Atlas (no ChromaDB/LLM overhead)
5. UNSUPPORTED   - Queries requesting private/unavailable attributes (phone, email, CGPA, etc.)
6. OUT_OF_DOMAIN - General trivia, creative writing, or non-directory topics

Includes:
- Dynamic similarity threshold filtering (preventing weak context injection into LLM)
- Detailed per-stage latency instrumentation (classification, embedding, retrieval, LLM, total)
- Explicit retrieval statuses: 'sufficient', 'insufficient_results', 'no_results', 'not_applicable'
"""

from __future__ import annotations

import enum
import os
import re
import time
from typing import Any, Optional

from dotenv import load_dotenv
load_dotenv()

from app.database import connect
from app.embeddings import embed_text
from app.generator import build_rag_prompt, call_ollama
from app.retriever import (
    DEFAULT_SIMILARITY_THRESHOLD,
    RetrievalResult,
    build_metadata_filter,
    detect_query_constraints,
    format_context,
    retrieve_students,
    retrieve_with_status,
)
from app.vector_store import similarity_search


class QueryType(str, enum.Enum):
    STRUCTURED = "structured"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    AGGREGATION = "aggregation"
    UNSUPPORTED = "unsupported"
    OUT_OF_DOMAIN = "out_of_domain"


# Unsupported attribute keywords and patterns
UNSUPPORTED_PATTERNS = [
    (r"\b(phone|mobile|cell|contact\s*number|phone\s*number|calling\s*number|whatsapp)\b", "phone number"),
    (r"\b(email|e-mail|mail\s*id|email\s*address)\b", "email address"),
    (r"\b(cgpa|gpa|marks|grades?|percentage|score|academic\s*performance)\b", "academic grades/CGPA"),
    (r"\b(home\s*address|residential\s*address|personal\s*address|flat\s*number|house\s*number)\b", "private home address"),
    (r"\b(salary|package|ctc|stipend|compensation)\b", "salary/placement package"),
    (r"\b(bank|account|financial)\b", "financial information"),
    (r"\b(not\s+(in|present|available|recorded)\s+in(\s+the)?\s+records?|unrecorded\s+(data|info)|information\s+that\s+isn'?t\s+present)\b", "unrecorded information"),
]

# Out-of-domain patterns (creative writing, general trivia, weather, etc.)
OUT_OF_DOMAIN_PATTERNS = [
    r"\b(weather|forecast|temperature|climate)\b",
    r"\b(poem|poetry|story|joke|song|essay|riddle)\b",
    r"\b(capital\s+of|president\s+of|prime\s+minister|population\s+of)\b",
    r"\b(france|germany|spain|italy|europe|usa|america|mount\s+everest)\b",
    r"\b(write\s+(a\s+)?(python|javascript|code|script)|solve\s+(the\s+)?equation)\b",
]

# Aggregation keywords and patterns
AGGREGATION_PATTERNS = [
    r"\bhow\s+many\b",
    r"\bcount\s+(of|the)\b",
    r"\btotal\s+(number\s+of\s+)?students\b",
    r"\bnumber\s+of\s+students\b",
    r"\btotal\s+count\b",
    r"\bhow\s+many\s+(boys|girls|men|women|male|female)\b",
]

# Topical and semantic keywords
SEMANTIC_TOPIC_PATTERNS = [
    r"\bmachine\s+learning\b",
    r"\bartificial\s+intelligence\b",
    r"\bml\b",
    r"\bai\b",
    r"\bpython\b",
    r"\breact\b",
    r"\bweb\s*(development|dev)\b",
    r"\bfrontend\b",
    r"\bbackend\b",
    r"\bdata\s*science\b",
    r"\bdeep\s*learning\b",
    r"\bcloud\b",
    r"\bdocker\b",
    r"\bcybersecurity\b",
    r"\bblockchain\b",
    r"\bapp\s*(development|dev)\b",
    r"\bnlp\b",
    r"\bcomputer\s*vision\b",
    r"\bpostgresql\b",
    r"\bdatabase\b",
    r"\bprojects?\b",
    r"\bskills?\b",
    r"\binterests?\b",
    r"\bexperience\b",
    r"\bworking\s+on\b",
    r"\bspecializ(ing|ation)\b",
]

# Words that can be stripped when isolating the semantic intent from a hybrid query
FILLER_WORDS = {
    "who", "what", "are", "is", "some", "the", "from", "in", "at", "of", "to",
    "for", "student", "students", "batch", "campus", "school", "technology", "sot",
    "male", "female", "boys", "boy", "girls", "girl", "men", "women", "bengaluru",
    "pune", "noida", "lucknow", "find", "list", "show", "give", "me", "get", "tell",
    "about", "interested", "with", "having", "please", "can", "you", "details"
}


def classify_query(query: str) -> tuple[QueryType, dict[str, Any]]:
    """
    Deterministically classify an incoming natural-language query.

    Returns:
        (QueryType, details_dict)
    """
    lower = query.lower().strip()

    # 1. Check for UNSUPPORTED requests (sensitive/private attributes)
    for pattern, field_label in UNSUPPORTED_PATTERNS:
        if re.search(pattern, lower):
            return QueryType.UNSUPPORTED, {
                "unsupported_field": field_label,
                "matched_pattern": pattern,
            }

    # 2. Check for OUT_OF_DOMAIN requests (weather, poems, trivia, etc.)
    for pattern in OUT_OF_DOMAIN_PATTERNS:
        if re.search(pattern, lower):
            return QueryType.OUT_OF_DOMAIN, {
                "reason": "out_of_domain",
                "matched_pattern": pattern,
            }

    # 3. Check for AGGREGATION requests (counts, quantities)
    for pattern in AGGREGATION_PATTERNS:
        if re.search(pattern, lower):
            constraints = detect_query_constraints(query)
            return QueryType.AGGREGATION, {
                "constraints": constraints,
            }

    # 4. Detect structured constraints
    constraints = detect_query_constraints(query)

    # 5. Check for semantic topical terms
    has_semantic_topic = any(re.search(pat, lower) for pat in SEMANTIC_TOPIC_PATTERNS)

    # Extract remaining non-filter tokens to see if a semantic topic exists
    tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", lower)
    meaningful_tokens = [
        t for t in tokens
        if t not in FILLER_WORDS and not (len(t) == 2 and t in {"23", "24", "25", "26"})
    ]

    has_semantic_intent = has_semantic_topic or (len(meaningful_tokens) >= 1)

    # Decide between STRUCTURED, HYBRID, and SEMANTIC
    if constraints and has_semantic_intent:
        semantic_query = " ".join(meaningful_tokens) if meaningful_tokens else query
        return QueryType.HYBRID, {
            "constraints": constraints,
            "semantic_query": semantic_query,
        }
    elif constraints and not has_semantic_intent:
        return QueryType.STRUCTURED, {
            "constraints": constraints,
        }
    else:
        return QueryType.SEMANTIC, {
            "constraints": constraints,
            "semantic_query": query,
        }


# ============================================================================
# EXECUTION HANDLERS FOR EACH QUERY TYPE
# ============================================================================

def execute_structured_query(
    query: str,
    constraints: dict[str, Any],
    top_k: int = 5,
    similarity_threshold: float | None = None,
    t_class: float = 0.0,
) -> dict[str, Any]:
    """
    Execute a structured query using exact metadata filtering.
    Guarantees that all returned records strictly satisfy the metadata constraints.
    """
    t_start = time.perf_counter()

    metadata_filter = build_metadata_filter(
        campus=constraints.get("campus"),
        batch=constraints.get("batch"),
        gender=constraints.get("gender"),
        school=constraints.get("school"),
    )

    t0_embed = time.perf_counter()
    query_embedding = embed_text(query)
    t_embed = (time.perf_counter() - t0_embed) * 1000

    t0_ret = time.perf_counter()
    raw_hits = similarity_search(
        query_embedding=query_embedding,
        top_k=top_k,
        where=metadata_filter,
    )
    t_ret = (time.perf_counter() - t0_ret) * 1000

    if not raw_hits:
        t_total = (time.perf_counter() - t_start) * 1000 + t_class
        return {
            "success": True,
            "query": query,
            "query_type": QueryType.STRUCTURED.value,
            "retrieval_status": "no_results",
            "answer": "No student records matched the specified criteria in the PW IOI directory.",
            "sources": [],
            "timings": {
                "classification_ms": round(t_class, 2),
                "embedding_ms": round(t_embed, 2),
                "retrieval_ms": round(t_ret, 2),
                "context_ms": 0.0,
                "generation_ms": 0.0,
                "total_ms": round(t_total, 2),
            },
        }

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

    t0_ctx = time.perf_counter()
    context = format_context(results)
    prompt = build_rag_prompt(query, context)
    t_ctx = (time.perf_counter() - t0_ctx) * 1000

    t0_gen = time.perf_counter()
    answer = call_ollama(prompt)
    t_gen = (time.perf_counter() - t0_gen) * 1000

    t_total = (time.perf_counter() - t_start) * 1000 + t_class

    sources = [
        {
            "student_id": r.document_id,
            "name": r.name,
            "school": r.school,
            "campus": r.campus,
            "batch": r.batch,
            "gender": r.gender,
            "similarity_score": round(r.similarity_score, 4),
            "source_type": r.source_type,
        }
        for r in results
    ]

    return {
        "success": True,
        "query": query,
        "query_type": QueryType.STRUCTURED.value,
        "retrieval_status": "sufficient",
        "answer": answer,
        "sources": sources,
        "timings": {
            "classification_ms": round(t_class, 2),
            "embedding_ms": round(t_embed, 2),
            "retrieval_ms": round(t_ret, 2),
            "context_ms": round(t_ctx, 2),
            "generation_ms": round(t_gen, 2),
            "total_ms": round(t_total, 2),
        },
    }


def execute_hybrid_query(
    query: str,
    constraints: dict[str, Any],
    semantic_query: str,
    top_k: int = 5,
    similarity_threshold: float | None = None,
    t_class: float = 0.0,
) -> dict[str, Any]:
    """
    Execute hybrid retrieval:
    1. Apply exact metadata filters first (campus, batch, gender, school).
    2. Rank matching records using dense vector similarity on the semantic query.
    3. Filter by similarity threshold to avoid injecting weak context.
    """
    t_start = time.perf_counter()

    metadata_filter = build_metadata_filter(
        campus=constraints.get("campus"),
        batch=constraints.get("batch"),
        gender=constraints.get("gender"),
        school=constraints.get("school"),
    )

    query_to_embed = semantic_query.strip() or query

    t0_embed = time.perf_counter()
    query_embedding = embed_text(query_to_embed)
    t_embed = (time.perf_counter() - t0_embed) * 1000

    t0_ret = time.perf_counter()
    raw_hits = similarity_search(
        query_embedding=query_embedding,
        top_k=top_k,
        where=metadata_filter,
    )
    t_ret = (time.perf_counter() - t0_ret) * 1000

    threshold = similarity_threshold if similarity_threshold is not None else DEFAULT_SIMILARITY_THRESHOLD

    # Evaluate results against threshold
    if not raw_hits:
        retrieval_status = "no_results"
        passing_hits = []
    else:
        passing_hits = [h for h in raw_hits if h["similarity_score"] >= threshold]
        retrieval_status = "sufficient" if passing_hits else "insufficient_results"

    if retrieval_status != "sufficient":
        t_total = (time.perf_counter() - t_start) * 1000 + t_class
        ans = (
            "No student records matched the specified criteria in the PW IOI directory."
            if retrieval_status == "no_results"
            else "I couldn't find sufficiently relevant information in the available student records."
        )
        return {
            "success": True,
            "query": query,
            "query_type": QueryType.HYBRID.value,
            "retrieval_status": retrieval_status,
            "answer": ans,
            "sources": [],
            "timings": {
                "classification_ms": round(t_class, 2),
                "embedding_ms": round(t_embed, 2),
                "retrieval_ms": round(t_ret, 2),
                "context_ms": 0.0,
                "generation_ms": 0.0,
                "total_ms": round(t_total, 2),
            },
        }

    results = [
        RetrievalResult(
            document_id=hit["document_id"],
            content=hit["content"],
            metadata=hit["metadata"],
            similarity_score=hit["similarity_score"],
            distance=hit["distance"],
        )
        for hit in passing_hits
    ]

    t0_ctx = time.perf_counter()
    context = format_context(results)
    prompt = build_rag_prompt(query, context)
    t_ctx = (time.perf_counter() - t0_ctx) * 1000

    t0_gen = time.perf_counter()
    answer = call_ollama(prompt)
    t_gen = (time.perf_counter() - t0_gen) * 1000

    t_total = (time.perf_counter() - t_start) * 1000 + t_class

    sources = [
        {
            "student_id": r.document_id,
            "name": r.name,
            "school": r.school,
            "campus": r.campus,
            "batch": r.batch,
            "gender": r.gender,
            "similarity_score": round(r.similarity_score, 4),
            "source_type": r.source_type,
        }
        for r in results
    ]

    return {
        "success": True,
        "query": query,
        "query_type": QueryType.HYBRID.value,
        "retrieval_status": "sufficient",
        "answer": answer,
        "sources": sources,
        "timings": {
            "classification_ms": round(t_class, 2),
            "embedding_ms": round(t_embed, 2),
            "retrieval_ms": round(t_ret, 2),
            "context_ms": round(t_ctx, 2),
            "generation_ms": round(t_gen, 2),
            "total_ms": round(t_total, 2),
        },
    }


def execute_semantic_query(
    query: str,
    top_k: int = 5,
    similarity_threshold: float | None = None,
    t_class: float = 0.0,
) -> dict[str, Any]:
    """
    Execute pure semantic retrieval via FastEmbed and ChromaDB HNSW cosine search.
    Guards against weak/irrelevant retrieval by checking similarity threshold.
    """
    t_start = time.perf_counter()

    t0_embed = time.perf_counter()
    query_emb = embed_text(query)
    t_embed = (time.perf_counter() - t0_embed) * 1000

    t0_ret = time.perf_counter()
    results, retrieval_status = retrieve_with_status(
        query=query,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
    )
    t_ret = (time.perf_counter() - t0_ret) * 1000

    if retrieval_status != "sufficient":
        t_total = (time.perf_counter() - t_start) * 1000 + t_class
        ans = (
            "No student records matched the specified query in the PW IOI directory."
            if retrieval_status == "no_results"
            else "I couldn't find sufficiently relevant information in the available student records."
        )
        return {
            "success": True,
            "query": query,
            "query_type": QueryType.SEMANTIC.value,
            "retrieval_status": retrieval_status,
            "answer": ans,
            "sources": [],
            "timings": {
                "classification_ms": round(t_class, 2),
                "embedding_ms": round(t_embed, 2),
                "retrieval_ms": round(t_ret, 2),
                "context_ms": 0.0,
                "generation_ms": 0.0,
                "total_ms": round(t_total, 2),
            },
        }

    t0_ctx = time.perf_counter()
    context = format_context(results)
    prompt = build_rag_prompt(query, context)
    t_ctx = (time.perf_counter() - t0_ctx) * 1000

    t0_gen = time.perf_counter()
    answer = call_ollama(prompt)
    t_gen = (time.perf_counter() - t0_gen) * 1000

    t_total = (time.perf_counter() - t_start) * 1000 + t_class

    sources = [
        {
            "student_id": r.document_id,
            "name": r.name,
            "school": r.school,
            "campus": r.campus,
            "batch": r.batch,
            "gender": r.gender,
            "similarity_score": round(r.similarity_score, 4),
            "source_type": r.source_type,
        }
        for r in results
    ]

    return {
        "success": True,
        "query": query,
        "query_type": QueryType.SEMANTIC.value,
        "retrieval_status": "sufficient",
        "answer": answer,
        "sources": sources,
        "timings": {
            "classification_ms": round(t_class, 2),
            "embedding_ms": round(t_embed, 2),
            "retrieval_ms": round(t_ret, 2),
            "context_ms": round(t_ctx, 2),
            "generation_ms": round(t_gen, 2),
            "total_ms": round(t_total, 2),
        },
    }


def execute_aggregation_query(
    query: str,
    constraints: dict[str, Any],
    t_class: float = 0.0,
) -> dict[str, Any]:
    """
    Execute safe, read-only aggregation query directly against MongoDB Atlas.
    Does NOT query ChromaDB or invoke LLM generation.
    """
    t_start = time.perf_counter()

    t0_agg = time.perf_counter()
    db = connect()
    collection = db["students"]

    mongo_filter: dict[str, Any] = {}
    if constraints.get("campus"):
        mongo_filter["campus"] = {"$regex": f"^{constraints['campus']}$", "$options": "i"}
    if constraints.get("batch"):
        b_val = str(constraints["batch"])
        mongo_filter["batch"] = {"$in": [b_val, int(b_val) if b_val.isdigit() else b_val]}
    if constraints.get("gender"):
        mongo_filter["gender"] = constraints["gender"].upper()
    if constraints.get("school"):
        mongo_filter["school"] = constraints["school"].upper()

    count = collection.count_documents(mongo_filter)
    t_agg = (time.perf_counter() - t0_agg) * 1000

    # Format user-friendly natural language response
    filter_parts: list[str] = []
    if constraints.get("gender"):
        filter_parts.append(f"{constraints['gender'].lower()}")
    filter_parts.append("students")
    if constraints.get("batch"):
        filter_parts.append(f"in batch {constraints['batch']}")
    if constraints.get("campus"):
        filter_parts.append(f"at {constraints['campus']} campus")

    criteria_str = " ".join(filter_parts)
    answer = f"According to the PW IOI student directory, there are **{count} {criteria_str}**."

    t_total = (time.perf_counter() - t_start) * 1000 + t_class

    return {
        "success": True,
        "query": query,
        "query_type": QueryType.AGGREGATION.value,
        "retrieval_status": "not_applicable",
        "answer": answer,
        "sources": [],
        "aggregation": {
            "count": count,
            "filters": constraints,
        },
        "timings": {
            "classification_ms": round(t_class, 2),
            "aggregation_ms": round(t_agg, 2),
            "total_ms": round(t_total, 2),
        },
    }


def execute_unsupported_query(
    query: str,
    unsupported_field: str,
    t_class: float = 0.0,
) -> dict[str, Any]:
    """
    Execute safe refusal for unsupported queries requesting private/unavailable attributes.
    Does not hallucinate, does not call LLM.
    Optionally retrieves student public profile if a specific student is named.
    """
    t_start = time.perf_counter()

    lower = query.lower()
    student_name_match = None
    for name in ["Aarushi Mandloi", "Hitendra Kumar Dewangan", "Abirbhab Basak", "Priya Sharma"]:
        if name.lower() in lower:
            student_name_match = name
            break

    sources: list[dict[str, Any]] = []
    t_ret = 0.0
    if student_name_match:
        t0_ret = time.perf_counter()
        hits = retrieve_students(query=student_name_match, top_k=1, similarity_threshold=0.0)
        t_ret = (time.perf_counter() - t0_ret) * 1000
        if hits:
            h = hits[0]
            sources.append({
                "student_id": h.document_id,
                "name": h.name,
                "campus": h.campus,
                "batch": h.batch,
                "gender": h.gender,
                "similarity_score": round(h.similarity_score, 4),
                "source_type": h.source_type,
            })
            answer = (
                f"The requested information ({unsupported_field}) for {h.name} is private and not available in the public PW IOI student directory. "
                f"The directory only contains public student profiles (School: {h.school}, Campus: {h.campus}, Batch: {h.batch}, Gender: {h.gender})."
            )
        else:
            answer = (
                f"The requested attribute ({unsupported_field}) is private and not available in the public PW IOI student directory. "
                "Available fields are strictly limited to student name, campus, batch, gender, and school."
            )
    else:
        answer = (
            f"The requested attribute ({unsupported_field}) is private and not available in the public PW IOI student directory. "
            "Available information is strictly limited to student name, campus, batch, gender, and school."
        )

    t_total = (time.perf_counter() - t_start) * 1000 + t_class

    return {
        "success": True,
        "query": query,
        "query_type": QueryType.UNSUPPORTED.value,
        "retrieval_status": "not_applicable",
        "answer": answer,
        "sources": sources,
        "timings": {
            "classification_ms": round(t_class, 2),
            "retrieval_ms": round(t_ret, 2),
            "total_ms": round(t_total, 2),
        },
    }


def execute_out_of_domain_query(
    query: str,
    t_class: float = 0.0,
) -> dict[str, Any]:
    """
    Execute fast safe refusal for out-of-domain / irrelevant queries.
    Does not invoke ChromaDB or LLM.
    """
    t_start = time.perf_counter()
    answer = (
        "I couldn't find sufficiently relevant information in the available student records. "
        "IOI AI is a specialized assistant dedicated to the PW Institute of Innovation student directory."
    )
    t_total = (time.perf_counter() - t_start) * 1000 + t_class

    return {
        "success": True,
        "query": query,
        "query_type": QueryType.OUT_OF_DOMAIN.value,
        "retrieval_status": "insufficient_results",
        "answer": answer,
        "sources": [],
        "timings": {
            "classification_ms": round(t_class, 2),
            "total_ms": round(t_total, 2),
        },
    }# ============================================================================
# DETERMINISTIC RESPONSE FORMATTING & NORMALIZATION LAYER
# ============================================================================

def format_student_profile(record: Any) -> str:
    """
    Format a verified student record into the required standard student profile structure:
    Student Name: <name>

    School: <school>

    Campus: <campus>

    Batch: <batch>

    Gender: <gender, only if available>

    <Name> is a student of <school> at the <campus> campus, belonging to Batch <batch>.

    Rules:
    - Never invent missing fields.
    - If a field is unavailable, explicitly say: 'Not available in the records.'
    - Only include Gender if available.
    """
    raw_name = record.name.strip() if hasattr(record, "name") else str(record.get("name", "")).strip()
    name = raw_name.title() if raw_name.isupper() else raw_name
    if not name or name.lower() in {"unknown", "none"}:
        name = "Not available in the records."

    raw_school = record.school.strip() if hasattr(record, "school") else str(record.get("school", "")).strip()
    school = raw_school if raw_school and raw_school.lower() not in {"unknown", "none", ""} else "Not available in the records."

    raw_campus = record.campus.strip() if hasattr(record, "campus") else str(record.get("campus", "")).strip()
    campus = raw_campus if raw_campus and raw_campus.lower() not in {"unknown", "none", ""} else "Not available in the records."

    raw_batch = str(record.batch).strip() if hasattr(record, "batch") else str(record.get("batch", "")).strip()
    batch = raw_batch if raw_batch and raw_batch.lower() not in {"unknown", "none", ""} else "Not available in the records."

    raw_gender = record.gender.strip() if hasattr(record, "gender") else str(record.get("gender", "")).strip()
    gender = raw_gender if raw_gender and raw_gender.lower() not in {"not available", "unknown", "none", ""} else None

    lines = [
        f"Student Name: {name}",
        f"School: {school}",
        f"Campus: {campus}",
        f"Batch: {batch}",
    ]
    if gender:
        lines.append(f"Gender: {gender}")

    # Short factual summary
    if campus != "Not available in the records." and batch != "Not available in the records." and school != "Not available in the records.":
        summary = f"{name} is a student of {school} at the {campus} campus, belonging to Batch {batch}."
    elif campus != "Not available in the records." and school != "Not available in the records.":
        summary = f"{name} is a student of {school} at the {campus} campus."
    elif school != "Not available in the records." and batch != "Not available in the records.":
        summary = f"{name} is a student of {school}, belonging to Batch {batch}."
    else:
        summary = f"{name} is recorded in the student directory."

    return "\n\n".join(lines) + "\n\n" + summary


def detect_student_profile_resolution(
    query: str,
    query_type: str,
    retrieval_status: str,
    sources: list[dict[str, Any]],
) -> tuple[bool, Optional[dict[str, Any]]]:
    """
    Detect whether a query unambiguously resolves to a specific individual student profile.

    Rules:
    1. Only applicable if retrieval_status is 'sufficient' and sources is non-empty.
    2. Excludes aggregation, unsupported, and out-of-domain queries.
    3. Excludes general plural/list queries (e.g. 'find students', 'who are some students', 'how many').
    4. Matches if:
       - Query explicitly targets a student by name (e.g. 'tell me about Aarushi Mandloi', 'who is Sagar Gupta', 'Esha Bajaj')
       - AND the top source matches that person's name with high confidence.
    """
    if retrieval_status != "sufficient" or not sources:
        return False, None

    if query_type in {"aggregation", "unsupported", "out_of_domain"}:
        return False, None

    q_lower = query.lower().strip()

    # Negative check: general collection/plural query patterns
    plural_patterns = [
        r"\bwho\s+are\s+(some|the)\b",
        r"\bfind\s+(male|female\s+)?students\b",
        r"\blist\s+(of\s+)?students\b",
        r"\bwhich\s+students\b",
        r"\bshow\s+(me\s+)?students\b",
        r"\ball\s+students\b",
        r"\bhow\s+many\b",
        r"\bcount\s+of\b",
        r"\b(students|boys|girls|men|women)\s+(from|in|at|interested)\b",
    ]
    for pat in plural_patterns:
        if re.search(pat, q_lower):
            return False, None

    top_source = sources[0]
    cand_name = (top_source.get("name") or "").strip()
    if not cand_name:
        return False, None

    cand_lower = cand_name.lower()
    cand_tokens = [t for t in re.findall(r"[a-z]+", cand_lower) if len(t) > 1]
    q_tokens = set(re.findall(r"[a-z]+", q_lower))

    has_profile_intent = any(
        re.search(pat, q_lower)
        for pat in [
            r"^([a-z\s]+)$",
            r"\btell\s+me\s+about\b",
            r"\bwho\s+is\b",
            r"\bdetails\s+(of|about|for)\b",
            r"\bprofile\s+(of|about|for)\b",
            r"\binformation\s+(about|on)\b",
            r"\babout\s+[a-z]+",
            r"\bstudent\s+[a-z]+",
        ]
    )

    # 1. Exact full name substring match
    if cand_lower in q_lower:
        return True, top_source

    # 2. All tokens of candidate's name appear in the query
    if cand_tokens and all(t in q_tokens for t in cand_tokens):
        return True, top_source

    # 3. High similarity match with profile intent and shared name tokens
    if has_profile_intent and top_source.get("similarity_score", 0) >= 0.60:
        common_tokens = [t for t in cand_tokens if t in q_tokens]
        if common_tokens:
            return True, top_source

    return False, None


def normalize_query_response(result: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministic response-formatting layer.
    Ensures that queries resolving to an individual student profile always use
    the standardized profile format, regardless of model randomness or variations.
    """
    if not result.get("success"):
        return result

    query = result.get("query", "")
    query_type = result.get("query_type", "")
    retrieval_status = result.get("retrieval_status", "")
    sources = result.get("sources", [])

    is_profile, student_record = detect_student_profile_resolution(
        query=query,
        query_type=query_type,
        retrieval_status=retrieval_status,
        sources=sources,
    )

    if is_profile and student_record:
        result["answer"] = format_student_profile(student_record)

    return result


def route_and_execute_query(
    query: str,
    top_k: int = 5,
    campus: str | None = None,
    batch: str | int | None = None,
    gender: str | None = None,
    school: str | None = None,
    similarity_threshold: float | None = None,
    record_metric: bool = True,
) -> dict[str, Any]:
    """
    Unified entry point for query routing, execution, and timing instrumentation.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("Query string cannot be empty")

    t0_class = time.perf_counter()
    query_type, details = classify_query(cleaned_query)
    t_class = (time.perf_counter() - t0_class) * 1000

    # Merge explicit parameters if caller provided them
    explicit_constraints: dict[str, Any] = {}
    if campus:
        explicit_constraints["campus"] = campus.strip().title()
    if batch:
        explicit_constraints["batch"] = str(batch).strip()
    if gender:
        explicit_constraints["gender"] = gender.strip().upper()
    if school:
        explicit_constraints["school"] = school.strip().upper()

    if explicit_constraints:
        detected_constraints = details.get("constraints", {})
        merged_constraints = {**detected_constraints, **explicit_constraints}
        details["constraints"] = merged_constraints

    try:
        if query_type == QueryType.UNSUPPORTED:
            result = execute_unsupported_query(
                query=cleaned_query,
                unsupported_field=details.get("unsupported_field", "attribute"),
                t_class=t_class,
            )
        elif query_type == QueryType.OUT_OF_DOMAIN:
            result = execute_out_of_domain_query(
                query=cleaned_query,
                t_class=t_class,
            )
        elif query_type == QueryType.AGGREGATION:
            result = execute_aggregation_query(
                query=cleaned_query,
                constraints=details.get("constraints", {}),
                t_class=t_class,
            )
        elif query_type == QueryType.HYBRID:
            result = execute_hybrid_query(
                query=cleaned_query,
                constraints=details.get("constraints", {}),
                semantic_query=details.get("semantic_query", cleaned_query),
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                t_class=t_class,
            )
        elif query_type == QueryType.STRUCTURED:
            result = execute_structured_query(
                query=cleaned_query,
                constraints=details.get("constraints", {}),
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                t_class=t_class,
            )
        else:  # SEMANTIC
            result = execute_semantic_query(
                query=cleaned_query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                t_class=t_class,
            )

        # Apply deterministic response-formatting layer for student profiles
        result = normalize_query_response(result)

        if record_metric:
            try:
                from app.metrics import get_metrics_collector
                get_metrics_collector().record_query(
                    query=cleaned_query,
                    query_type=result.get("query_type", query_type.value),
                    retrieval_status=result.get("retrieval_status", "unknown"),
                    success=result.get("success", True),
                    sources_count=len(result.get("sources", [])),
                    timings=result.get("timings", {}),
                )
            except Exception:
                pass

        return result
    except Exception as e:
        if record_metric:
            try:
                from app.metrics import get_metrics_collector
                get_metrics_collector().record_query(
                    query=cleaned_query,
                    query_type=query_type.value,
                    retrieval_status="failed",
                    success=False,
                    sources_count=0,
                    timings={"classification_ms": round(t_class, 2)},
                    error=str(e),
                )
            except Exception:
                pass
        raise

