"""
Latency Benchmark for Step 8J Intelligent Query Routing & Hybrid Retrieval.

Measures:
1. Structured query latency (metadata filter + LLM)
2. Semantic query latency (dense vector search + LLM)
3. Hybrid query latency (metadata filter + topical vector search + LLM)
4. Aggregation query latency (direct MongoDB count - no vector search, no LLM)
5. Unsupported query latency (deterministic safe refusal guardrail)
"""

from __future__ import annotations

import statistics
import time
from app.query_router import route_and_execute_query

BENCHMARK_CASES = [
    ("STRUCTURED", "male students from batch 26"),
    ("SEMANTIC", "students interested in machine learning"),
    ("HYBRID", "female students from Pune interested in machine learning"),
    ("AGGREGATION", "how many students are in Bengaluru"),
    ("UNSUPPORTED", "what is Aarushi Mandloi's phone number"),
]


def run_benchmark(num_runs: int = 2):
    print("=" * 75)
    print("IOI AI — STEP 8J QUERY ROUTING LATENCY BENCHMARK")
    print(f"Benchmarking {len(BENCHMARK_CASES)} categories across {num_runs} runs each")
    print("=" * 75)

    # Warmup
    print("Warming up database and embedding models...")
    _ = route_and_execute_query("warmup", top_k=1)
    _ = route_and_execute_query("how many students are in Bengaluru")
    print("Warmup complete.\n")

    results: dict[str, list[float]] = {}

    for category, query in BENCHMARK_CASES:
        print(f"[{category}] '{query}'")
        run_times: list[float] = []
        for r in range(num_runs):
            t0 = time.perf_counter()
            res = route_and_execute_query(query, top_k=3)
            elapsed = (time.perf_counter() - t0) * 1000  # ms
            run_times.append(elapsed)
            print(f"   Run {r + 1}: {elapsed:.1f} ms | Type: {res['query_type']}")
        results[category] = run_times

    print("\n" + "=" * 75)
    print("STEP 8J BENCHMARK RESULTS SUMMARY")
    print("=" * 75)
    print(f"{'Query Category':<16} | {'Avg Latency':<14} | {'Step 8I Baseline':<18} | {'Speedup / Change':<18}")
    print("-" * 75)

    step_8i_baseline = {
        "STRUCTURED": 4030.0,
        "SEMANTIC": 4960.0,
        "HYBRID": 4750.0,
        "AGGREGATION": 4230.0,  # 8I had to use vector search + LLM approximation
        "UNSUPPORTED": 2360.0,  # 8I had to invoke LLM to generate refusal
    }

    for cat, times in results.items():
        avg_ms = statistics.mean(times)
        base_ms = step_8i_baseline.get(cat, 4750.0)
        if avg_ms < 1000:
            avg_str = f"{avg_ms:.1f} ms"
        else:
            avg_str = f"{avg_ms / 1000:.2f} s"

        if base_ms < 1000:
            base_str = f"{base_ms:.1f} ms"
        else:
            base_str = f"{base_ms / 1000:.2f} s"

        if avg_ms < base_ms:
            speedup = base_ms / avg_ms
            diff_str = f"{speedup:.1f}x faster"
        else:
            diff_str = "Comparable"

        print(f"{cat:<16} | {avg_str:<14} | {base_str:<18} | {diff_str:<18}")

    print("=" * 75)


if __name__ == "__main__":
    run_benchmark(num_runs=2)
