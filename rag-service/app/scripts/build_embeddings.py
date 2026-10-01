"""
Build embeddings for RAG student documents.

Reads RAG documents from data/processed/student_documents.json,
generates dense vector embeddings using the configured embedding provider,
and writes the output to data/processed/student_embeddings.json.

Usage:
    cd rag-service
    python -m app.scripts.build_embeddings
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Load .env before anything else
from dotenv import load_dotenv  # type: ignore[import-not-found,import-untyped]
load_dotenv()

# Add project root so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.embeddings import embed_documents


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"
INPUT_FILE = DATA_DIR / "student_documents.json"
OUTPUT_FILE = DATA_DIR / "student_embeddings.json"

BATCH_SIZE = 64


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build embeddings for RAG student documents.")
    parser.add_argument("--input", "-i", type=Path, default=None, help="Input documents JSON file")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output embeddings JSON file")
    parser.add_argument("--batch-size", "-b", type=int, default=BATCH_SIZE, help="Batch size for embedding")
    args = parser.parse_args()

    input_file = args.input or Path(os.environ.get("DOCUMENTS_INPUT_FILE", INPUT_FILE))
    output_file = args.output or Path(os.environ.get("EMBEDDINGS_OUTPUT_FILE", OUTPUT_FILE))
    batch_size = args.batch_size

    if not input_file.exists():
        print(f"[build_embeddings] Error: Input file not found: {input_file}", file=sys.stderr)
        print("[build_embeddings] Run 'python -m app.scripts.build_documents' first.", file=sys.stderr)
        sys.exit(1)

    print(f"[build_embeddings] Reading documents from {input_file}...")
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            documents = json.load(f)
    except Exception as e:
        print(f"[build_embeddings] Failed to read or parse input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(documents, list):
        print(f"[build_embeddings] Error: Expected list of documents, got {type(documents).__name__}", file=sys.stderr)
        sys.exit(1)

    total_docs = len(documents)
    print(f"[build_embeddings] Loaded {total_docs} RAG documents")

    if total_docs == 0:
        print("[build_embeddings] No documents found to embed.", file=sys.stderr)
        sys.exit(1)

    # Extract contents while tracking document indices
    contents: list[str] = []
    for idx, doc in enumerate(documents):
        content = doc.get("content")
        if not content:
            print(f"[build_embeddings] Error: Document at index {idx} (ID: {doc.get('document_id')}) has empty content.", file=sys.stderr)
            sys.exit(1)
        contents.append(content)

    print(f"[build_embeddings] Generating embeddings (batch size: {batch_size})...")
    start_time = time.time()

    try:
        embeddings = embed_documents(contents, batch_size=batch_size)
    except Exception as e:
        print(f"\n[build_embeddings] Error during embedding generation: {e}", file=sys.stderr)
        sys.exit(1)

    duration = time.time() - start_time
    total_embeddings = len(embeddings)

    if total_embeddings != total_docs:
        print(
            f"[build_embeddings] Error: Mismatch between input documents ({total_docs}) "
            f"and generated embeddings ({total_embeddings}). Aborting without writing file.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate embeddings
    dim = len(embeddings[0]) if embeddings else 0
    for idx, emb in enumerate(embeddings):
        if not isinstance(emb, list) or len(emb) != dim:
            print(
                f"[build_embeddings] Error: Inconsistent embedding dimension at index {idx}. "
                f"Expected {dim}, got {len(emb) if isinstance(emb, list) else type(emb)}.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Assemble output records
    output_records: list[dict] = []
    for doc, emb in zip(documents, embeddings):
        output_records.append({
            "document_id": doc["document_id"],
            "content": doc["content"],
            "metadata": doc["metadata"],
            "embedding": emb,
        })

    # Save to JSON
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_records, f, indent=2, ensure_ascii=False)

    print("=" * 50)
    print("EMBEDDING GENERATION COMPLETE")
    print("=" * 50)
    print(f"  Documents read:       {total_docs}")
    print(f"  Embeddings generated: {total_embeddings}")
    print(f"  Embedding dimensions: {dim}")
    print(f"  Processing time:      {duration:.2f}s")
    print(f"  Output file:          {output_file}")
    print("=" * 50)

    # Display small sample without printing complete vectors
    if output_records:
        sample = output_records[0]
        preview_vector = [round(v, 4) for v in sample["embedding"][:5]]
        print("\n[build_embeddings] Example embedded record:")
        print(f"  Document ID:          {sample['document_id']}")
        print(f"  Embedding Dimension:  {len(sample['embedding'])}")
        print(f"  First 5 vector values: {preview_vector} ...")
        print(f"  Student Name:         {sample['metadata'].get('name')}")
        print(f"  Campus:               {sample['metadata'].get('campus')}")
        print(f"  Batch:                {sample['metadata'].get('batch')}")


if __name__ == "__main__":
    main()
