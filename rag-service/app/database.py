"""
MongoDB connection module for the RAG service.

Connects to the same MongoDB Atlas database used by the Node.js backend.
"""

import os
import sys
from pymongo import MongoClient
from pymongo.database import Database


_client: MongoClient | None = None
_db: Database | None = None


def connect() -> Database:
    """
    Connect to MongoDB using environment variables.
    Returns the database handle. Reuses the connection if already connected.
    """
    global _client, _db

    if _db is not None:
        return _db

    uri = os.environ.get("MONGODB_URI")
    db_name = os.environ.get("MONGODB_DATABASE", "ioi_ai")

    if not uri:
        print("[rag-service] MONGODB_URI is not set. See .env.example.", file=sys.stderr)
        sys.exit(1)

    try:
        import certifi
        ca_file = certifi.where()
    except ImportError:
        ca_file = None

    try:
        if ca_file:
            _client = MongoClient(uri, tlsCAFile=ca_file)
        else:
            _client = MongoClient(uri)
        # Force a connection test
        _client.admin.command("ping")
        _db = _client[db_name]
        print(f"[rag-service] MongoDB connected — database: {db_name}")
        return _db
    except Exception as e:
        print(f"[rag-service] MongoDB connection failed: {e}", file=sys.stderr)
        sys.exit(1)


def disconnect() -> None:
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        print("[rag-service] MongoDB disconnected")
