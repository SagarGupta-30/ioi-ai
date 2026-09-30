"""
Test Suite for Query Router & Hybrid Retrieval (Step 8J).

Verifies deterministic classification, execution paths, structured metadata filtering,
aggregation counts, and safe refusal for unsupported queries.
"""

from __future__ import annotations

import sys
import time
from typing import Any

from app.query_router import QueryType, classify_query, route_and_execute_query

TEST_CASES = [
    {
        "id": 1,
        "query": "male students from batch 26",
        "expected_type": QueryType.STRUCTURED,
        "description": "Structured query with batch and gender constraints",
        "check_fn": lambda res: (
            res["query_type"] == "structured"
            and len(res["sources"]) > 0
            and all(s["gender"] == "MALE" and str(s["batch"]) == "26" for s in res["sources"])
        ),
    },
    {
        "id": 2,
        "query": "female students from Pune",
        "expected_type": QueryType.STRUCTURED,
        "description": "Structured query with campus and gender constraints",
        "check_fn": lambda res: (
            res["query_type"] == "structured"
            and len(res["sources"]) > 0
            and all(s["gender"] == "FEMALE" and s["campus"] == "Pune" for s in res["sources"])
        ),
    },
    {
        "id": 3,
        "query": "students interested in machine learning",
        "expected_type": QueryType.SEMANTIC,
        "description": "Pure semantic topical search",
        "check_fn": lambda res: (
            res["query_type"] == "semantic"
            and len(res["sources"]) > 0
        ),
    },
    {
        "id": 4,
        "query": "female students from Pune interested in machine learning",
        "expected_type": QueryType.HYBRID,
        "description": "Hybrid query combining structured filter with topical search",
        "check_fn": lambda res: (
            res["query_type"] == "hybrid"
            and len(res["sources"]) > 0
            and all(s["gender"] == "FEMALE" and s["campus"] == "Pune" for s in res["sources"])
        ),
    },
    {
        "id": 5,
        "query": "how many students are in Bengaluru",
        "expected_type": QueryType.AGGREGATION,
        "description": "MongoDB count aggregation for Bengaluru campus",
        "check_fn": lambda res: (
            res["query_type"] == "aggregation"
            and res.get("aggregation", {}).get("count") == 453
            and "453" in res["answer"]
        ),
    },
    {
        "id": 6,
        "query": "how many male students are there",
        "expected_type": QueryType.AGGREGATION,
        "description": "MongoDB count aggregation for male students",
        "check_fn": lambda res: (
            res["query_type"] == "aggregation"
            and res.get("aggregation", {}).get("count") == 946
            and "946" in res["answer"]
        ),
    },
    {
        "id": 7,
        "query": "tell me about Aarushi Mandloi",
        "expected_type": QueryType.SEMANTIC,
        "description": "Semantic student profile query",
        "check_fn": lambda res: (
            res["query_type"] == "semantic"
            and len(res["sources"]) > 0
            and any("Aarushi" in s["name"] for s in res["sources"])
        ),
    },
    {
        "id": 8,
        "query": "what is Aarushi Mandloi's phone number",
        "expected_type": QueryType.UNSUPPORTED,
        "description": "Unsupported query requesting private phone number",
        "check_fn": lambda res: (
            res["query_type"] == "unsupported"
            and ("private" in res["answer"].lower() or "not available" in res["answer"].lower())
            and "phone number" in res["answer"].lower()
        ),
    },
    {
        "id": 9,
        "query": "what is the CGPA of students in Lucknow?",
        "expected_type": QueryType.UNSUPPORTED,
        "description": "Unsupported query requesting unavailable academic grades",
        "check_fn": lambda res: (
            res["query_type"] == "unsupported"
            and ("private" in res["answer"].lower() or "not available" in res["answer"].lower())
        ),
    },
]


def run_tests():
    print("=" * 75)
    print("IOI AI — STEP 8J QUERY ROUTER & HYBRID RETRIEVAL TEST SUITE")
    print(f"Testing {len(TEST_CASES)} representative test cases")
    print("=" * 75)

    passed_count = 0

    for tc in TEST_CASES:
        t_start = time.perf_counter()
        q = tc["query"]
        print(f"\n[Test #{tc['id']}] Query: '{q}'")
        print(f"  Description: {tc['description']}")

        # 1. Classification check
        q_type, details = classify_query(q)
        expected = tc["expected_type"]
        if q_type != expected:
            print(f"  ✗ Classification Failed: Expected '{expected.value}', got '{q_type.value}'")
            continue
        print(f"  ✓ Classification: {q_type.value} | Details: {details}")

        # 2. Execution check
        try:
            res = route_and_execute_query(q, top_k=3)
            elapsed = time.perf_counter() - t_start
            
            passed = tc["check_fn"](res)
            if passed:
                passed_count += 1
                print(f"  ✓ Execution PASSED ({elapsed:.2f}s) | Query Type: {res['query_type']}")
                print(f"    Answer Preview: {res['answer'][:120]}...")
                if res.get("sources"):
                    print(f"    Sources: {len(res['sources'])} items")
                if res.get("aggregation"):
                    print(f"    Aggregation Result: {res['aggregation']}")
            else:
                print(f"  ✗ Execution Verification FAILED ({elapsed:.2f}s)")
                print(f"    Response was: {res}")
        except Exception as e:
            print(f"  ✗ Execution Error: {e}")

    print("\n" + "=" * 75)
    print(f"QUERY ROUTER TEST SUMMARY: {passed_count} / {len(TEST_CASES)} Passed")
    print("=" * 75)

    if passed_count != len(TEST_CASES):
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
