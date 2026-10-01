"""
IOI AI — RAG HTTP Service.

FastAPI application providing:
- GET  /api/health      Health check including ChromaDB and Ollama status
- POST /api/rag/query   End-to-end RAG answer generation with source traceability

Reuses the existing embedding, vector store, retriever, and generator modules.
"""

import logging
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("rag-service")

from app.generator import (
    DEFAULT_HF_MODEL,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    generate_rag_response,
)
from app.metrics import get_metrics_collector
from app.query_router import route_and_execute_query
from app.vector_store import load_index

app = FastAPI(
    title="IOI AI — RAG Service",
    description="Local Retrieval-Augmented Generation API for PW IOI School of Technology",
    version="1.0.0",
)

# Enable CORS for frontend integration
cors_origins_env = os.environ.get("CORS_ORIGIN", "*")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] if cors_origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return clean HTTP 400 on input validation failure."""
    errors = exc.errors()
    first_msg = errors[0].get("msg") if errors else "Invalid request body"
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "error": first_msg},
    )


class RAGQueryRequest(BaseModel):
    """Schema for incoming RAG query."""

    query: str = Field(..., min_length=1, max_length=1000, description="Natural-language search question (1-1000 characters)")
    top_k: Optional[int] = Field(default=5, ge=1, le=50, description="Number of context records (1-50)")
    campus: Optional[str] = Field(default=None, description="Optional campus filter")
    batch: Optional[str] = Field(default=None, description="Optional batch filter")
    gender: Optional[str] = Field(default=None, description="Optional gender filter")
    school: Optional[str] = Field(default=None, description="Optional school filter")


class SourceItem(BaseModel):
    """Traceable source document reference."""

    student_id: str
    name: str
    campus: str
    batch: str
    gender: str
    similarity_score: float
    source_type: str


class RAGQueryResponse(BaseModel):
    """Structured response from the RAG pipeline."""

    success: bool
    query: str
    query_type: str = Field(default="semantic", description="Classification: structured, semantic, hybrid, aggregation, unsupported, out_of_domain")
    retrieval_status: str = Field(default="sufficient", description="sufficient, insufficient_results, no_results, not_applicable")
    answer: str
    sources: list[dict[str, Any]]
    aggregation: Optional[dict[str, Any]] = Field(default=None, description="Structured count result for aggregation queries")
    timings: Optional[dict[str, float]] = Field(default=None, description="Per-stage latency breakdown in ms")


@app.get("/")
@app.get("/health")
@app.get("/api/health")
def health_check() -> dict[str, Any]:
    """
    Health check endpoint reporting:
    - Service overall status
    - Local ChromaDB vector store availability & record count
    - Local Ollama LLM runtime availability & configured model
    """
    # 1. Check ChromaDB
    vector_store_status = "unavailable"
    total_records = 0
    try:
        col = load_index()
        total_records = col.count()
        vector_store_status = "ready"
    except Exception as e:
        vector_store_status = f"error: {str(e)}"

    # 2. Check LLM Runtime
    llm_provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if llm_provider == "huggingface":
        hf_token = os.environ.get("HF_TOKEN")
        hf_model = os.environ.get("HF_MODEL", DEFAULT_HF_MODEL)
        if not hf_token:
            llm_status = "unconfigured: missing HF_TOKEN"
            llm_ready = False
        else:
            llm_status = "ready"
            llm_ready = True
        llm_info = {
            "provider": "huggingface",
            "status": llm_status,
            "model": hf_model,
            "endpoint": "https://api-inference.huggingface.co",
        }
    else:
        ollama_host = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        model_name = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        ollama_status = "unavailable"
        try:
            req = urllib.request.Request(f"{ollama_host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    ollama_status = "ready"
        except Exception:
            ollama_status = "unreachable"
        llm_ready = (ollama_status == "ready")
        llm_info = {
            "provider": "ollama",
            "status": ollama_status,
            "model": model_name,
            "endpoint": ollama_host,
        }

    overall_ok = (vector_store_status == "ready") and llm_ready

    return {
        "status": "ok" if overall_ok else "degraded",
        "service": "ioi-ai-rag-service",
        "vector_store": {
            "status": vector_store_status,
            "indexed_records": total_records,
        },
        "embeddings": {
            "provider": os.environ.get("EMBEDDING_PROVIDER", "fastembed"),
            "model": os.environ.get("EMBEDDING_MODEL") or (
                "sentence-transformers/all-MiniLM-L6-v2"
                if os.environ.get("EMBEDDING_PROVIDER", "").lower() in ("sentence-transformers", "sentence_transformers")
                else os.environ.get("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
            ),
            "dimensions": 384,
        },
        "llm_runtime": llm_info,
    }


@app.post("/api/rag/query", response_model=RAGQueryResponse)
def handle_rag_query(payload: RAGQueryRequest) -> RAGQueryResponse:
    """
    Handle natural-language RAG query:
    Validates input -> Queries ChromaDB -> Constructs context -> Runs local LLM -> Returns answer with sources.
    """
    cleaned_query = payload.query.strip()
    if not cleaned_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty or whitespace only.",
        )

    try:
        result = route_and_execute_query(
            query=cleaned_query,
            top_k=payload.top_k or 5,
            campus=payload.campus,
            batch=payload.batch,
            gender=payload.gender,
            school=payload.school,
        )
    except Exception as e:
        logger.exception(f"RAG query execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing the RAG query.",
        )

    # Format sources matching the exact required schema
    formatted_sources = [
        {
            "student_id": s.get("student_id") or s.get("document_id"),
            "name": s.get("name"),
            "campus": s.get("campus"),
            "batch": s.get("batch"),
            "gender": s.get("gender"),
            "similarity_score": round(s.get("similarity_score", 0.0), 4),
            "source_type": s.get("source_type"),
        }
        for s in result.get("sources", [])
    ]

    return RAGQueryResponse(
        success=True,
        query=result["query"],
        query_type=result.get("query_type", "semantic"),
        retrieval_status=result.get("retrieval_status", "sufficient"),
        answer=result["answer"],
        sources=formatted_sources,
        aggregation=result.get("aggregation"),
        timings=result.get("timings"),
    )


@app.get("/api/metrics")
def get_metrics_endpoint(
    limit: int = Query(default=50, ge=1, le=200, description="Max recent records to return"),
    query_type: Optional[str] = Query(default=None, description="Filter by query type"),
    status: Optional[str] = Query(default=None, description="Filter by retrieval status"),
) -> dict[str, Any]:
    """
    Retrieve recent raw query metrics records.
    """
    collector = get_metrics_collector()
    records = collector.get_metrics(limit=limit, query_type=query_type, retrieval_status=status)
    return {
        "success": True,
        "count": len(records),
        "metrics": records,
    }


@app.get("/api/metrics/summary")
def get_metrics_summary_endpoint() -> dict[str, Any]:
    """
    Retrieve aggregated performance, latency percentiles, and distribution statistics.
    """
    collector = get_metrics_collector()
    summary = collector.get_summary()
    return {
        "success": True,
        "summary": summary,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
