"""
End-to-end RAG verification test script for IOI AI.

Tests the full pipeline:
Query -> FastEmbed embedding -> ChromaDB retrieval -> Grounded prompt -> Local LLM -> Answer

Tests all 5 required queries plus 1 unsupported query to verify hallucination refusal.

Usage:
    cd rag-service
    python -m app.scripts.test_rag
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add project root so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.generator import generate_rag_response


TEST_QUERIES = [
    {
        "id": 1,
        "query": "Who are some students from Bengaluru?",
        "expected_behavior": "Should list students from Bengaluru campus based on retrieved records.",
    },
    {
        "id": 2,
        "query": "Which students have machine learning or artificial intelligence skills?",
        "expected_behavior": "Should highlight Priya Sharma (the synthetic profile with ML/AI skills) and note that public records do not have skills listed.",
    },
    {
        "id": 3,
        "query": "Find male students from batch 26.",
        "expected_behavior": "Should list male students enrolled in batch 26 from the retrieved records.",
    },
    {
        "id": 4,
        "query": "Tell me about Aarushi Mandloi.",
        "expected_behavior": "Should state Aarushi Mandloi's school, campus, batch, gender, and source provenance.",
    },
    {
        "id": 5,
        "query": "What projects has Aarushi Mandloi built?",
        "expected_behavior": "Must NOT hallucinate projects; should state projects are 'Not available' / missing from records.",
    },
    {
        "id": 6,
        "query": "What is Aarushi Mandloi's phone number?",
        "expected_behavior": "UNSUPPORTED: Must refuse to invent contact info; state phone number is not available in records.",
    },
]


def print_separator(title: str = "") -> None:
    width = 70
    if title:
        padding = max(2, (width - len(title) - 2) // 2)
        print(f"\n{'=' * padding} {title} {'=' * padding}")
    else:
        print(f"{'=' * width}")


def run_test_query(test_item: dict) -> None:
    qid = test_item["id"]
    query = test_item["query"]

    print_separator(f"TEST QUERY #{qid}")
    print(f"Question: \"{query}\"")
    print(f"Goal:     {test_item['expected_behavior']}\n")

    t0 = time.time()
    try:
        response = generate_rag_response(query=query, top_k=3)
    except Exception as e:
        print(f"Error during RAG generation: {e}", file=sys.stderr)
        return

    latency = time.time() - t0

    print("Retrieved documents (sources):")
    for idx, src in enumerate(response["sources"], start=1):
        print(
            f"  [{idx}] {src['name']} | Campus: {src['campus']} | "
            f"Batch: {src['batch']} | Score: {src['similarity_score']:.4f} | "
            f"Source: {src['source_type']}"
        )

    print(f"\nGenerated answer (Latency: {latency:.2f}s):")
    print("-" * 50)
    print(response["answer"])
    print("-" * 50)


def main() -> None:
    print_separator("IOI AI — STEP 8E END-TO-END RAG PIPELINE TEST")
    print("Architecture: FastEmbed -> ChromaDB -> Local LLM (Ollama)")
    print("Testing 5 standard queries + 1 unsupported hallucination test\n")

    for item in TEST_QUERIES:
        run_test_query(item)

    print_separator("RAG PIPELINE VERIFICATION COMPLETE")


if __name__ == "__main__":
    main()
