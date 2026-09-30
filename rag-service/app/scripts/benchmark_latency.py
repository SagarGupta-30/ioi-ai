"""
Latency Benchmarking Script for IOI AI RAG Pipeline.

Measures the 4 key stages:
1. Query embedding latency (FastEmbed)
2. ChromaDB retrieval latency (HNSW Vector Search)
3. Ollama generation latency (llama3.2:1b)
4. Total end-to-end RAG latency
"""

from __future__ import annotations

import statistics
import time
from typing import Any

from app.embeddings import embed_text
from app.generator import call_ollama, build_rag_prompt
from app.retriever import format_context, retrieve_students
from app.vector_store import similarity_search

BENCHMARK_QUERIES = [
    "Who are some students from Bengaluru campus?",
    "Find male students from batch 26.",
    "Which students have machine learning or Python skills?",
    "Tell me about Aarushi Mandloi.",
    "What is the contact number of students in Pune?",
]


def run_benchmark(num_runs: int = 2):
    print("=" * 70)
    print("IOI AI — STEP 8I PART F: LATENCY PERFORMANCE BENCHMARK")
    print(f"Benchmarking {len(BENCHMARK_QUERIES)} queries across {num_runs} runs each")
    print("=" * 70)

    # Warmup
    print("Warming up embedding and vector store...")
    _ = similarity_search(query_text="warmup", top_k=1)
    print("Warmup complete. Starting benchmarks...\n")

    embed_times: list[float] = []
    retrieve_times: list[float] = []
    llm_times: list[float] = []
    total_times: list[float] = []

    for idx, query in enumerate(BENCHMARK_QUERIES, 1):
        print(f"[{idx}/{len(BENCHMARK_QUERIES)}] Query: '{query}'")

        query_embed_times: list[float] = []
        query_retrieve_times: list[float] = []
        query_llm_times: list[float] = []
        query_total_times: list[float] = []

        for r in range(num_runs):
            t_start = time.perf_counter()

            # 1. Embedding latency
            t0 = time.perf_counter()
            q_emb = embed_text(query)
            t_emb = (time.perf_counter() - t0) * 1000  # ms

            # 2. Retrieval latency (ChromaDB query)
            t0 = time.perf_counter()
            results = retrieve_students(query=query, top_k=3)
            t0_chroma = time.perf_counter()
            _ = similarity_search(query_embedding=q_emb, top_k=3)
            t_chroma = (time.perf_counter() - t0_chroma) * 1000

            # 3. LLM Generation latency
            context = format_context(results)
            prompt = build_rag_prompt(query, context)
            t0 = time.perf_counter()
            _ = call_ollama(prompt)
            t_gen = (time.perf_counter() - t0) * 1000  # ms

            t_tot = (time.perf_counter() - t_start) * 1000

            query_embed_times.append(t_emb)
            query_retrieve_times.append(t_chroma)
            query_llm_times.append(t_gen)
            query_total_times.append(t_tot)

        avg_e = statistics.mean(query_embed_times)
        avg_r = statistics.mean(query_retrieve_times)
        avg_l = statistics.mean(query_llm_times)
        avg_t = statistics.mean(query_total_times)

        print(
            f"       Embed: {avg_e:.1f}ms | Chroma: {avg_r:.1f}ms | LLM: {avg_l / 1000:.2f}s | Total: {avg_t / 1000:.2f}s"
        )

        embed_times.extend(query_embed_times)
        retrieve_times.extend(query_retrieve_times)
        llm_times.extend(query_llm_times)
        total_times.extend(query_total_times)

    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY (All Queries & Runs)")
    print("=" * 70)
    print(
        f"{'Stage':<32} | {'Avg':<12} | {'Min':<10} | {'Max':<10}"
    )
    print("-" * 70)
    print(
        f"{'1. Query Embedding (FastEmbed)':<32} | {statistics.mean(embed_times):.2f} ms     | {min(embed_times):.2f} ms  | {max(embed_times):.2f} ms"
    )
    print(
        f"{'2. ChromaDB Vector Search':<32} | {statistics.mean(retrieve_times):.2f} ms     | {min(retrieve_times):.2f} ms  | {max(retrieve_times):.2f} ms"
    )
    print(
        f"{'3. Ollama Generation (llama3.2)':<32} | {statistics.mean(llm_times) / 1000:.2f} s       | {min(llm_times) / 1000:.2f} s    | {max(llm_times) / 1000:.2f} s"
    )
    print(
        f"{'4. Total RAG Pipeline':<32} | {statistics.mean(total_times) / 1000:.2f} s       | {min(total_times) / 1000:.2f} s    | {max(total_times) / 1000:.2f} s"
    )
    print("=" * 70)


if __name__ == "__main__":
    run_benchmark(num_runs=2)
