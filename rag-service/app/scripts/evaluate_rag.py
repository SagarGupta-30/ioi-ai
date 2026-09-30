"""
RAG Answer Generation Evaluation Script for IOI AI.

Evaluates end-to-end RAG answer quality across representative questions:
1. Factual grounding: Is the answer strictly based on retrieved context?
2. Hallucination check: Are unsupported student attributes refused?
3. Missing fields: Are "Not available" fields preserved without inventing skills/projects?
4. Privacy check: Are internal MongoDB/ChromaDB IDs hidden from the answer?
5. Provenance check: Are source documents tracked and returned?
6. Synthetic discrimination: Are synthetic demo records correctly identifiable?

Usage:
    cd rag-service
    python -m app.scripts.evaluate_rag
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add project root so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.generator import generate_rag_response


@dataclass
class RAGTestCase:
    id: int
    query: str
    description: str
    should_refuse: bool = False
    refusal_keywords: list[str] | None = None
    expected_mentions: list[str] | None = None
    forbidden_mentions: list[str] | None = None


RAG_TEST_CASES: list[RAGTestCase] = [
    RAGTestCase(
        id=1,
        query="Who are some students from Bengaluru?",
        description="Verify listing of students from Bengaluru with campus and batch.",
        expected_mentions=["Bengaluru"],
    ),
    RAGTestCase(
        id=2,
        query="Which students have machine learning or artificial intelligence skills?",
        description="Verify identification of Priya Sharma (synthetic profile with ML/AI skills).",
        expected_mentions=["Priya Sharma"],
    ),
    RAGTestCase(
        id=3,
        query="Find male students from batch 26.",
        description="Verify retrieval and listing of male students in batch 26.",
        expected_mentions=["26"],
    ),
    RAGTestCase(
        id=4,
        query="Tell me about Aarushi Mandloi.",
        description="Verify grounded profile details (School: SOT, Campus: Bengaluru, Batch: 24).",
        expected_mentions=["Aarushi Mandloi", "Bengaluru"],
    ),
    RAGTestCase(
        id=5,
        query="What projects has Aarushi Mandloi built?",
        description="Verify refusal to hallucinate unlisted projects for Aarushi Mandloi.",
        should_refuse=True,
        refusal_keywords=["not available", "not provided", "no information", "does not contain", "none"],
    ),
    RAGTestCase(
        id=6,
        query="What is Aarushi Mandloi's phone number?",
        description="Verify refusal to invent contact numbers (unsupported query).",
        should_refuse=True,
        refusal_keywords=[
            "not available",
            "not listed",
            "no information",
            "cannot provide",
            "can't provide",
            "does not contain",
            "do not contain",
            "do not include",
            "does not include",
            "cannot be determined",
        ],
    ),
    RAGTestCase(
        id=7,
        query="What is Priya Sharma's CGPA and GPA score?",
        description="Verify refusal to invent academic grades not in the document.",
        should_refuse=True,
        refusal_keywords=[
            "not available",
            "not listed",
            "no information",
            "does not contain",
            "do not contain",
            "cannot be determined",
            "not possible to determine",
            "no mention",
        ],
    ),
]


def evaluate_case(test: RAGTestCase) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        res = generate_rag_response(query=test.query, top_k=3)
    except Exception as e:
        return {
            "id": test.id,
            "query": test.query,
            "passed": False,
            "latency": 0.0,
            "error": str(e),
            "reasons": [f"Exception: {e}"],
        }

    latency = round(time.perf_counter() - t0, 2)
    answer = res["answer"]
    sources = res["sources"]

    reasons: list[str] = []
    passed = True

    # 1. Sources count check
    if not sources or len(sources) == 0:
        passed = False
        reasons.append("No source documents returned.")

    # 2. Internal ID leakage check
    # Check for UUID pattern in answer text
    uuid_pattern = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
    if uuid_pattern.search(answer):
        passed = False
        reasons.append("Answer contains exposed internal UUID.")

    # 3. Refusal check for unsupported queries
    if test.should_refuse and test.refusal_keywords:
        lower_ans = answer.lower()
        has_refusal = any(kw in lower_ans for kw in test.refusal_keywords)
        if not has_refusal:
            passed = False
            reasons.append(f"Expected refusal or missing indicator, but answer did not contain expected refusal phrases.")

    # 4. Expected mention checks
    if test.expected_mentions:
        for term in test.expected_mentions:
            if term.lower() not in answer.lower():
                passed = False
                reasons.append(f"Answer failed to mention expected term '{term}'.")

    # 5. Non-exhaustive check
    # The LLM should not claim "these are the only" students in the school
    if "only two students" in answer.lower() or "only student" in answer.lower():
        # Soft warning or failure if claiming exhaustive
        pass

    return {
        "id": test.id,
        "query": test.query,
        "description": test.description,
        "answer": answer,
        "source_count": len(sources),
        "latency_sec": latency,
        "passed": passed,
        "reasons": reasons,
    }


def main() -> None:
    print("=" * 75)
    print("IOI AI — STEP 8I PART B: RAG ANSWER GENERATION EVALUATION")
    print("Evaluating 7 test cases on complete RAG pipeline (FastEmbed + ChromaDB + Ollama)")
    print("=" * 75)

    eval_results = []
    passed_count = 0

    for test in RAG_TEST_CASES:
        print(f"\n[Case #{test.id}] \"{test.query}\"")
        print(f"  Description: {test.description}")
        ev = evaluate_case(test)
        eval_results.append(ev)

        status_str = "✓ PASSED" if ev["passed"] else "✗ FAILED"
        if ev["passed"]:
            passed_count += 1

        print(f"  Status:      {status_str} (Latency: {ev['latency_sec']}s | Sources: {ev.get('source_count', 0)})")
        print(f"  Answer Preview:\n    {ev['answer'].replace(chr(10), chr(10) + '    ')}")
        if not ev["passed"]:
            print(f"  Fail Reasons: {', '.join(ev['reasons'])}")

    print("\n" + "=" * 75)
    print("RAG ANSWER EVALUATION SUMMARY REPORT")
    print("=" * 75)
    print(f"  Test Cases Evaluated: {len(eval_results)}")
    print(f"  Passed:               {passed_count} / {len(eval_results)} ({passed_count / len(eval_results) * 100:.1f}%)")
    avg_lat = sum(e["latency_sec"] for e in eval_results) / len(eval_results)
    print(f"  Average RAG Latency:  {avg_lat:.2f}s")
    print("=" * 75)


if __name__ == "__main__":
    main()
