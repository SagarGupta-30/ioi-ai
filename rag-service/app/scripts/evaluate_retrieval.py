"""
Retrieval Layer Evaluation Script for IOI AI.

Evaluates semantic search and structured retrieval across 10 representative queries:
1. students in Bengaluru
2. male students from batch 26
3. female students from Pune
4. students interested in machine learning
5. students from Noida
6. students from batch 24
7. Tell me about Aarushi Mandloi
8. students with Python skills
9. students with web development interests
10. students with quantum computing PhD (unsupported / out-of-domain)

Measures:
- Embedding latency vs ChromaDB retrieval latency
- Similarity scores (min, max, avg)
- Constraint satisfaction for queries with structured attributes
- Summary evaluation metrics

Usage:
    cd rag-service
    python -m app.scripts.evaluate_retrieval
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add project root so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.embeddings import embed_text
from app.retriever import retrieve_students, RetrievalResult
from app.vector_store import load_index


@dataclass
class QueryTestCase:
    id: int
    query: str
    expected_campus: str | None = None
    expected_batch: str | None = None
    expected_gender: str | None = None
    expected_skill: str | None = None
    is_unsupported: bool = False


TEST_DATASET: list[QueryTestCase] = [
    QueryTestCase(id=1, query="students in Bengaluru", expected_campus="Bengaluru"),
    QueryTestCase(id=2, query="male students from batch 26", expected_gender="MALE", expected_batch="26"),
    QueryTestCase(id=3, query="female students from Pune", expected_gender="FEMALE", expected_campus="Pune"),
    QueryTestCase(id=4, query="students interested in machine learning", expected_skill="machine learning"),
    QueryTestCase(id=5, query="students from Noida", expected_campus="Noida"),
    QueryTestCase(id=6, query="students from batch 24", expected_batch="24"),
    QueryTestCase(id=7, query="Tell me about Aarushi Mandloi"),
    QueryTestCase(id=8, query="students with Python skills", expected_skill="Python"),
    QueryTestCase(id=9, query="students with web development interests", expected_skill="web development"),
    QueryTestCase(id=10, query="students with quantum computing PhD", is_unsupported=True),
]


def evaluate_retrieval_query(test: QueryTestCase, top_k: int = 5) -> dict[str, Any]:
    # 1. Measure query embedding time
    t0 = time.perf_counter()
    query_emb = embed_text(test.query)
    emb_latency_ms = (time.perf_counter() - t0) * 1000

    # 2. Measure ChromaDB search time
    t1 = time.perf_counter()
    results = retrieve_students(query=test.query, top_k=top_k)
    search_latency_ms = (time.perf_counter() - t1) * 1000
    total_latency_ms = emb_latency_ms + search_latency_ms

    scores = [r.similarity_score for r in results]
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # 3. Constraint checking
    constraint_checks = []
    if test.expected_campus:
        campus_matches = sum(1 for r in results if r.campus.lower() == test.expected_campus.lower())
        constraint_checks.append(f"Campus '{test.expected_campus}': {campus_matches}/{len(results)} matches")

    if test.expected_batch:
        batch_matches = sum(1 for r in results if str(r.batch) == str(test.expected_batch))
        constraint_checks.append(f"Batch '{test.expected_batch}': {batch_matches}/{len(results)} matches")

    if test.expected_gender:
        gender_matches = sum(1 for r in results if r.gender.upper() == test.expected_gender.upper())
        constraint_checks.append(f"Gender '{test.expected_gender}': {gender_matches}/{len(results)} matches")

    return {
        "id": test.id,
        "query": test.query,
        "top_k_returned": len(results),
        "emb_latency_ms": round(emb_latency_ms, 2),
        "search_latency_ms": round(search_latency_ms, 2),
        "total_latency_ms": round(total_latency_ms, 2),
        "min_score": round(min_score, 4),
        "max_score": round(max_score, 4),
        "avg_score": round(avg_score, 4),
        "constraint_checks": constraint_checks,
        "results": [
            {
                "name": r.name,
                "campus": r.campus,
                "batch": r.batch,
                "gender": r.gender,
                "score": round(r.similarity_score, 4),
                "source_type": r.source_type,
            }
            for r in results
        ],
    }


def main() -> None:
    print("=" * 75)
    print("IOI AI — STEP 8I PART A: RETRIEVAL QUALITY EVALUATION")
    print("Evaluating 10 representative queries on ChromaDB (1,097 documents)")
    print("=" * 75)

    # Pre-warm embedding model to ensure pure latency measurement
    _ = embed_text("warmup query")

    all_evals = []
    for test in TEST_DATASET:
        ev = evaluate_retrieval_query(test, top_k=5)
        all_evals.append(ev)

        print(f"\n[Query #{ev['id']}] \"{ev['query']}\"")
        print(f"  Latency:      Total: {ev['total_latency_ms']}ms (Embed: {ev['emb_latency_ms']}ms | Search: {ev['search_latency_ms']}ms)")
        print(f"  Similarity:   Max: {ev['max_score']:.4f} | Avg: {ev['avg_score']:.4f} | Min: {ev['min_score']:.4f}")
        if ev["constraint_checks"]:
            print(f"  Constraints:  {', '.join(ev['constraint_checks'])}")
        print("  Top Results:")
        for rank, r in enumerate(ev["results"][:3], start=1):
            print(f"    #{rank} {r['name']} ({r['campus']}, Batch {r['batch']}, {r['gender']}) - Score: {r['score']} [{r['source_type']}]")

    # Summary Statistics
    total_queries = len(all_evals)
    avg_total_lat = sum(e["total_latency_ms"] for e in all_evals) / total_queries
    avg_emb_lat = sum(e["emb_latency_ms"] for e in all_evals) / total_queries
    avg_search_lat = sum(e["search_latency_ms"] for e in all_evals) / total_queries
    overall_avg_sim = sum(e["avg_score"] for e in all_evals) / total_queries

    print("\n" + "=" * 75)
    print("RETRIEVAL EVALUATION SUMMARY REPORT")
    print("=" * 75)
    print(f"  Total test queries evaluated:    {total_queries}")
    print(f"  Average query embedding latency: {avg_emb_lat:.2f} ms")
    print(f"  Average ChromaDB search latency: {avg_search_lat:.2f} ms")
    print(f"  Average total retrieval latency: {avg_total_lat:.2f} ms")
    print(f"  Average top-5 similarity score:  {overall_avg_sim:.4f}")
    print("=" * 75)


if __name__ == "__main__":
    main()
