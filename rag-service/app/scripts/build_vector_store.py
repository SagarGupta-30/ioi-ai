"""
Build local vector store index for IOI AI.

Reads existing pre-computed embeddings from data/processed/student_embeddings.json,
indexes all vectors, documents, and metadata into ChromaDB, and performs a sample
similarity search to verify retrieval.

Usage:
    cd rag-service
    python -m app.scripts.build_vector_store
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv()

# Add project root so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.vector_store import (
    create_or_replace_index,
    get_vector_store_dir,
    similarity_search,
)


INPUT_FILE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "processed"
    / "student_embeddings.json"
)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build local vector store index for IOI AI.")
    parser.add_argument("--input", "-i", type=Path, default=None, help="Input precomputed embeddings JSON file")
    parser.add_argument("--store-dir", "-s", type=Path, default=None, help="Target directory for ChromaDB storage")
    parser.add_argument("--collection-name", "-c", type=str, default=None, help="ChromaDB collection name")
    args = parser.parse_args()

    input_file = args.input or Path(os.environ.get("EMBEDDINGS_INPUT_FILE", INPUT_FILE))
    store_dir = args.store_dir or get_vector_store_dir()
    collection_name = args.collection_name or os.environ.get("CHROMA_COLLECTION_NAME", "students")

    if not input_file.exists():
        print(f"[build_vector_store] Error: Input file not found: {input_file}", file=sys.stderr)
        print("[build_vector_store] Please run 'python -m app.scripts.build_embeddings' first.", file=sys.stderr)
        sys.exit(1)

    print(f"[build_vector_store] Reading embeddings from {input_file}...")
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception as e:
        print(f"[build_vector_store] Failed to parse {input_file}: {e}", file=sys.stderr)
        sys.exit(1)

    total_records = len(records)
    print(f"[build_vector_store] Found {total_records} precomputed embedding records")

    if total_records == 0:
        print("[build_vector_store] Error: No records found to index.", file=sys.stderr)
        sys.exit(1)

    print(f"[build_vector_store] Indexing into local ChromaDB at {store_dir}...")

    start_time = time.time()
    try:
        indexed_count = create_or_replace_index(records, persist_dir=store_dir, collection_name=collection_name)
    except Exception as e:
        print(f"\n[build_vector_store] Indexing failed: {e}", file=sys.stderr)
        sys.exit(1)

    duration = time.time() - start_time

    if indexed_count != total_records:
        print(
            f"[build_vector_store] Error: Indexed count ({indexed_count}) does not match "
            f"input records ({total_records}).",
            file=sys.stderr,
        )
        sys.exit(1)

    dim = len(records[0]["embedding"]) if records else 0

    print("=" * 50)
    print("VECTOR STORE INDEXING COMPLETE")
    print("=" * 50)
    print(f"  Records read:         {total_records}")
    print(f"  Vectors indexed:      {indexed_count}")
    print(f"  Embedding dimensions: {dim}")
    print(f"  Similarity metric:    Cosine distance (HNSW)")
    print(f"  Storage location:     {store_dir}")
    print(f"  Indexing time:        {duration:.2f}s")
    print("=" * 50)

    # Verification similarity search
    sample_query = "machine learning and artificial intelligence projects in Bengaluru"
    print(f"\n[build_vector_store] Running verification similarity search...")
    print(f"  Sample Query: \"{sample_query}\"")
    print(f"  Top K: 2")

    search_start = time.time()
    results = similarity_search(
        query_text=sample_query,
        top_k=2,
        persist_dir=store_dir,
        collection_name=collection_name,
    )
    search_duration = time.time() - search_start

    print(f"  Search completed in {search_duration * 1000:.1f}ms")
    print("\n--- Search Results ---")
    for rank, res in enumerate(results, start=1):
        meta = res["metadata"]
        print(f"\nResult #{rank} [Similarity: {res['similarity_score']:.4f} | Distance: {res['distance']:.4f}]:")
        print(f"  Name:    {meta.get('name')}")
        print(f"  Campus:  {meta.get('campus')}")
        print(f"  Batch:   {meta.get('batch')}")
        print(f"  School:  {meta.get('school')}")
        print(f"  Source:  {meta.get('source_type')} ({meta.get('source_status')})")
        print(f"  ID:      {res['document_id']}")


if __name__ == "__main__":
    main()
