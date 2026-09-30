"""
Build RAG documents from MongoDB student records.

Reads all students from the ioi_ai database, converts each into a
RAG document, and saves the result to data/processed/student_documents.json.

Usage:
    cd rag-service
    python -m app.scripts.build_documents
"""

import json
import os
import sys
from pathlib import Path

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv()

# Add project root so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.database import connect, disconnect
from app.document_builder import build_document


OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "student_documents.json"


def main() -> None:
    db = connect()
    collection = db["students"]

    # Read all student records
    print("[build_documents] Reading students from MongoDB...")
    cursor = collection.find({})
    records = list(cursor)
    total_students = len(records)
    print(f"[build_documents] Found {total_students} student records\n")

    # Convert to RAG documents
    documents: list[dict] = []
    public_count = 0
    synthetic_count = 0
    skipped = 0

    for record in records:
        doc = build_document(record)
        if doc is None:
            skipped += 1
            continue

        documents.append(doc.to_dict())

        source_type = doc.metadata.source_type
        if source_type == "pwioi_public_api":
            public_count += 1
        elif source_type == "synthetic":
            synthetic_count += 1

    # Save to JSON
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    print("=" * 50)
    print("[build_documents] DOCUMENT GENERATION COMPLETE")
    print("=" * 50)
    print(f"  Students read:        {total_students}")
    print(f"  Documents created:    {len(documents)}")
    print(f"  Public records:       {public_count}")
    print(f"  Synthetic/demo:       {synthetic_count}")
    print(f"  Skipped (invalid):    {skipped}")
    print(f"  Output file:          {OUTPUT_FILE}")
    print("=" * 50)

    # Show one example
    if documents:
        print("\n[build_documents] Example document:\n")
        example = documents[0]
        print(example["content"])
        print(f"\nMetadata: {json.dumps(example['metadata'], indent=2)}")

    disconnect()


if __name__ == "__main__":
    main()
