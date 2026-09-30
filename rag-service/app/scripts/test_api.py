"""
API test script for the IOI AI RAG HTTP service.

Verifies:
1. GET  /api/health      (Vector store and Ollama health checks)
2. POST /api/rag/query   (Valid query with source metadata returned)
3. POST /api/rag/query   (Invalid empty query returning HTTP 400)
4. POST /api/rag/query   (Invalid top_k returning HTTP 400)

Usage:
    cd rag-service
    python -m app.scripts.test_api
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from starlette.testclient import TestClient
from app.main import app


def print_separator(title: str = "") -> None:
    width = 65
    if title:
        padding = max(2, (width - len(title) - 2) // 2)
        print(f"\n{'=' * padding} {title} {'=' * padding}")
    else:
        print(f"{'=' * width}")


def main() -> None:
    print_separator("IOI AI — STEP 8F RAG API TEST SUITE")
    client = TestClient(app)

    # ---------------------------------------------------------
    # Test 1: Health Check Endpoint
    # ---------------------------------------------------------
    print("\n[Test 1] Testing GET /api/health...")
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    health_data = resp.json()

    print(f"  Status code: {resp.status_code}")
    print(f"  Response:    {json.dumps(health_data, indent=2)}")

    assert health_data["status"] == "ok", "Expected overall status == 'ok'"
    assert health_data["vector_store"]["status"] == "ready", "Vector store not ready"
    assert health_data["vector_store"]["indexed_records"] == 1097, "Expected 1097 indexed records"
    assert health_data["llm_runtime"]["status"] == "ready", "LLM runtime not ready"
    print("✓ Test 1 Passed: /api/health is fully healthy (1,097 vectors + Ollama ready)")

    # ---------------------------------------------------------
    # Test 2: Valid RAG Query
    # ---------------------------------------------------------
    print("\n[Test 2] Testing POST /api/rag/query with valid query...")
    payload = {
        "query": "Find male students from batch 26.",
        "top_k": 3,
    }
    resp = client.post("/api/rag/query", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    query_data = resp.json()

    print(f"  Status code: {resp.status_code}")
    print(f"  Query:       {query_data['query']}")
    print(f"  Answer:      {query_data['answer']}")
    print(f"  Sources count: {len(query_data['sources'])}")

    assert query_data["success"] is True
    assert query_data["query"] == payload["query"]
    assert len(query_data["answer"]) > 10
    assert len(query_data["sources"]) == 3

    # Check source metadata attributes
    first_source = query_data["sources"][0]
    print(f"  Sample source item: {json.dumps(first_source, indent=2)}")
    for key in ["student_id", "name", "campus", "batch", "gender", "similarity_score", "source_type"]:
        assert key in first_source, f"Missing '{key}' in source item"
        assert first_source[key] is not None, f"'{key}' cannot be None"

    print("✓ Test 2 Passed: Valid RAG query returned grounded answer and complete sources list")

    # ---------------------------------------------------------
    # Test 3: Invalid Empty Query (Validation Error)
    # ---------------------------------------------------------
    print("\n[Test 3] Testing POST /api/rag/query with empty string...")
    resp = client.post("/api/rag/query", json={"query": ""})
    print(f"  Status code: {resp.status_code}")
    print(f"  Response:    {resp.text}")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"

    # Also test whitespace-only query
    resp_ws = client.post("/api/rag/query", json={"query": "     "})
    print(f"  Whitespace query status: {resp_ws.status_code}")
    assert resp_ws.status_code == 400, f"Expected 400 for whitespace, got {resp_ws.status_code}"
    print("✓ Test 3 Passed: Empty and whitespace queries properly rejected with HTTP 400")

    # ---------------------------------------------------------
    # Test 4: Invalid top_k (Bounds Validation Error)
    # ---------------------------------------------------------
    print("\n[Test 4] Testing POST /api/rag/query with top_k out of bounds (100)...")
    resp_bounds = client.post("/api/rag/query", json={"query": "students in Bengaluru", "top_k": 100})
    print(f"  Status code: {resp_bounds.status_code}")
    print(f"  Response:    {resp_bounds.text}")
    assert resp_bounds.status_code == 400, f"Expected 400, got {resp_bounds.status_code}"
    print("✓ Test 4 Passed: top_k exceeding sensible limit (>50) rejected with HTTP 400")

    print_separator("ALL API TESTS PASSED SUCCESSFULLY")


if __name__ == "__main__":
    main()
