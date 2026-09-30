"""
Test script for the IOI AI retrieval layer.

Executes required test queries and metadata filtering tests against the local
ChromaDB vector store. No MongoDB or external API calls required.

Usage:
    cd rag-service
    python -m app.scripts.test_retrieval
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.embeddings import embed_text
from app.retriever import retrieve_students, format_context


def print_separator(title: str = "") -> None:
    width = 65
    if title:
        padding = (width - len(title) - 2) // 2
        print(f"\n{'=' * padding} {title} {'=' * padding}")
    else:
        print(f"{'=' * width}")


def display_results(query: str, results: list, extra_info: str = "") -> None:
    print_separator(f"QUERY: \"{query}\"")
    if extra_info:
        print(f"Filter / Note: {extra_info}")
    print(f"Top-K Results Returned: {len(results)}\n")

    for rank, res in enumerate(results, start=1):
        print(f"Result #{rank}:")
        print(f"  Similarity Score:  {res.similarity_score:.4f} (Distance: {res.distance:.4f})")
        print(f"  Student Name:      {res.name}")
        print(f"  Campus:            {res.campus}")
        print(f"  Batch:             {res.batch}")
        print(f"  Gender:            {res.gender}")
        print(f"  Source Type:       {res.source_type} ({res.source_status})")
        print(f"  Document ID:       {res.document_id}")

        # Short content preview (first 2-3 lines or max 120 chars)
        preview_lines = [line.strip() for line in res.content.splitlines() if line.strip()]
        preview = " | ".join(preview_lines[:3])
        if len(preview) > 130:
            preview = preview[:127] + "..."
        print(f"  Content Preview:   {preview}")
        print()


def main() -> None:
    print_separator("IOI AI RETRIEVAL LAYER VERIFICATION")
    print("Testing local ChromaDB vector retrieval using FastEmbed (384 dimensions)")

    # 1. Verify query embedding dimension
    test_emb = embed_text("verification ping")
    assert len(test_emb) == 384, f"Expected 384 dimensions, got {len(test_emb)}"
    print(f"✓ Query embedding model loaded: 384-dimensional dense vectors verified")

    # 2. Test Query 1: "students in Bengaluru"
    q1 = "students in Bengaluru"
    t0 = time.time()
    r1 = retrieve_students(query=q1, top_k=3)
    t1 = time.time()
    display_results(q1, r1, extra_info=f"Latency: {(t1 - t0) * 1000:.1f}ms")

    # 3. Test Query 2: "students interested in machine learning and artificial intelligence"
    q2 = "students interested in machine learning and artificial intelligence"
    t0 = time.time()
    r2 = retrieve_students(query=q2, top_k=3)
    t1 = time.time()
    display_results(q2, r2, extra_info=f"Latency: {(t1 - t0) * 1000:.1f}ms")

    # 4. Test Query 3: "male students from batch 26"
    q3 = "male students from batch 26"
    t0 = time.time()
    r3 = retrieve_students(query=q3, top_k=3)
    t1 = time.time()
    display_results(q3, r3, extra_info=f"Latency: {(t1 - t0) * 1000:.1f}ms")

    # 5. Test Metadata Filtering Separately
    # Query: "students" with campus="Bengaluru"
    filter_query = "students"
    filter_campus = "Bengaluru"
    t0 = time.time()
    filtered_results = retrieve_students(
        query=filter_query,
        top_k=5,
        campus=filter_campus,
    )
    t1 = time.time()
    display_results(
        filter_query,
        filtered_results,
        extra_info=f"Applied Filter: campus='{filter_campus}' | Latency: {(t1 - t0) * 1000:.1f}ms",
    )

    # Validate that every single result strictly obeys the filter
    for r in filtered_results:
        assert (
            r.campus == filter_campus
        ), f"Filter violation: Expected campus '{filter_campus}', got '{r.campus}'"

    print("✓ Metadata Filter Verification Passed: All 5 returned students strictly match campus='Bengaluru'")

    # 6. Verify combined multi-filter: campus="Pune" and gender="FEMALE"
    multi_filtered = retrieve_students(
        query="technology student",
        top_k=3,
        campus="Pune",
        gender="FEMALE",
    )
    for r in multi_filtered:
        assert r.campus == "Pune", f"Expected Pune, got {r.campus}"
        assert r.gender == "FEMALE", f"Expected FEMALE, got {r.gender}"
    print("✓ Multi-Filter Verification Passed: Combined filters (campus='Pune' AND gender='FEMALE') strictly obeyed")

    # 7. Verify context formatting utility
    context_preview = format_context(r1[:2])
    print_separator("SAMPLE FORMATTED CONTEXT FOR FUTURE LLM")
    print(context_preview)
    print_separator("RETRIEVAL VERIFICATION COMPLETE")


if __name__ == "__main__":
    main()
