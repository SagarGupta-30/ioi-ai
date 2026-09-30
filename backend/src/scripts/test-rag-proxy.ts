/**
 * Step 8G Backend RAG Proxy Verification Script
 *
 * Tests the Node/Express backend at http://localhost:5001/api/rag/query:
 * 1. Valid RAG query (checks success, answer, and sources metadata)
 * 2. Empty query validation (expects HTTP 400)
 * 3. Invalid top_k validation (expects HTTP 400)
 * 4. RAG service unavailable handling (unit test of error wrapper)
 *
 * Usage:
 *   npx tsx src/scripts/test-rag-proxy.ts
 */

import "dotenv/config";
import { queryRAGService, RAGServiceError } from "../services/rag/client";

const BACKEND_URL = `http://localhost:${process.env.PORT || 5001}`;

function printSeparator(title = "") {
  const width = 65;
  if (title) {
    const pad = Math.max(2, Math.floor((width - title.length - 2) / 2));
    console.log(`\n${"=".repeat(pad)} ${title} ${"=".repeat(pad)}`);
  } else {
    console.log("=".repeat(width));
  }
}

async function testBackendRAG() {
  printSeparator("STEP 8G BACKEND RAG PROXY TEST SUITE");
  console.log(`Target Backend: ${BACKEND_URL}`);

  let passed = 0;
  let total = 4;

  // -------------------------------------------------------------------------
  // Test 1: Valid RAG Query
  // -------------------------------------------------------------------------
  console.log("\n[Test 1] Testing POST /api/rag/query with valid query...");
  try {
    const payload = {
      query: "Find male students from batch 26.",
      top_k: 3,
    };

    const res = await fetch(`${BACKEND_URL}/api/rag/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data: any = await res.json();
    console.log(`  HTTP Status: ${res.status}`);
    console.log(`  Success:     ${data.success}`);
    console.log(`  Query:       "${data.query}"`);
    console.log(`  Answer:      ${data.answer}`);
    console.log(`  Sources:     ${data.sources?.length || 0} items`);

    if (res.status === 200 && data.success && data.sources?.length > 0) {
      console.log(`  Sample source: ${data.sources[0].name} (${data.sources[0].campus}, Batch ${data.sources[0].batch}) - Score: ${data.sources[0].similarity_score}`);
      console.log("✓ Test 1 Passed: Valid query successfully proxied and returned grounded sources.");
      passed++;
    } else {
      console.error("✗ Test 1 Failed: Unexpected response body or status.", data);
    }
  } catch (err) {
    console.error("✗ Test 1 Error:", err);
  }

  // -------------------------------------------------------------------------
  // Test 2: Empty Query Validation
  // -------------------------------------------------------------------------
  console.log("\n[Test 2] Testing POST /api/rag/query with empty query string...");
  try {
    const res = await fetch(`${BACKEND_URL}/api/rag/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "   " }),
    });

    const data: any = await res.json();
    console.log(`  HTTP Status: ${res.status}`);
    console.log(`  Response:    ${JSON.stringify(data)}`);

    if (res.status === 400 && data.success === false) {
      console.log("✓ Test 2 Passed: Backend rejected empty query with HTTP 400.");
      passed++;
    } else {
      console.error("✗ Test 2 Failed: Expected HTTP 400.", data);
    }
  } catch (err) {
    console.error("✗ Test 2 Error:", err);
  }

  // -------------------------------------------------------------------------
  // Test 3: Invalid top_k Validation
  // -------------------------------------------------------------------------
  console.log("\n[Test 3] Testing POST /api/rag/query with out-of-bounds top_k (100)...");
  try {
    const res = await fetch(`${BACKEND_URL}/api/rag/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "students", top_k: 100 }),
    });

    const data: any = await res.json();
    console.log(`  HTTP Status: ${res.status}`);
    console.log(`  Response:    ${JSON.stringify(data)}`);

    if (res.status === 400 && data.success === false) {
      console.log("✓ Test 3 Passed: Backend rejected out-of-bounds top_k with HTTP 400.");
      passed++;
    } else {
      console.error("✗ Test 3 Failed: Expected HTTP 400.", data);
    }
  } catch (err) {
    console.error("✗ Test 3 Error:", err);
  }

  // -------------------------------------------------------------------------
  // Test 4: RAG Service Error / Unavailable Handling
  // -------------------------------------------------------------------------
  console.log("\n[Test 4] Testing RAG client error handling when target endpoint is unreachable...");
  try {
    const originalUrl = process.env.RAG_SERVICE_URL;
    process.env.RAG_SERVICE_URL = "http://localhost:59999"; // Non-existent port

    let caughtError: RAGServiceError | null = null;
    try {
      await queryRAGService({ query: "test" }, 2000);
    } catch (e: any) {
      caughtError = e;
    } finally {
      process.env.RAG_SERVICE_URL = originalUrl;
    }

    if (caughtError && (caughtError.statusCode === 503 || caughtError.statusCode === 504)) {
      console.log(`  Caught expected RAGServiceError (${caughtError.statusCode}): ${caughtError.message}`);
      console.log("✓ Test 4 Passed: Unreachable RAG service properly handled with service error.");
      passed++;
    } else {
      console.error("✗ Test 4 Failed: Expected RAGServiceError 503/504, got:", caughtError);
    }
  } catch (err) {
    console.error("✗ Test 4 Error:", err);
  }

  // -------------------------------------------------------------------------
  // Test 5: Proxy GET /api/rag/metrics
  // -------------------------------------------------------------------------
  total++;
  console.log("\n[Test 5] Testing GET /api/rag/metrics...");
  try {
    const res = await fetch(`${BACKEND_URL}/api/rag/metrics?limit=10`);
    const data: any = await res.json();
    console.log(`  HTTP Status: ${res.status}`);
    console.log(`  Success:     ${data.success}`);
    console.log(`  Count:       ${data.count}`);

    if (res.status === 200 && data.success && Array.isArray(data.metrics)) {
      console.log("✓ Test 5 Passed: /api/rag/metrics returned metrics array successfully.");
      passed++;
    } else {
      console.error("✗ Test 5 Failed: Unexpected metrics response:", data);
    }
  } catch (err) {
    console.error("✗ Test 5 Error:", err);
  }

  // -------------------------------------------------------------------------
  // Test 6: Proxy GET /api/rag/metrics/summary
  // -------------------------------------------------------------------------
  total++;
  console.log("\n[Test 6] Testing GET /api/rag/metrics/summary...");
  try {
    const res = await fetch(`${BACKEND_URL}/api/rag/metrics/summary`);
    const data: any = await res.json();
    console.log(`  HTTP Status: ${res.status}`);
    console.log(`  Success:     ${data.success}`);
    console.log(`  Total Queries: ${data.summary?.total_queries}`);

    if (res.status === 200 && data.success && data.summary?.latency_stats) {
      console.log("✓ Test 6 Passed: /api/rag/metrics/summary returned aggregated statistics.");
      passed++;
    } else {
      console.error("✗ Test 6 Failed: Unexpected metrics summary response:", data);
    }
  } catch (err) {
    console.error("✗ Test 6 Error:", err);
  }

  printSeparator(`TEST RESULTS: ${passed}/${total} PASSED`);
  if (passed === total) {
    process.exit(0);
  } else {
    process.exit(1);
  }
}

testBackendRAG();

