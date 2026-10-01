#!/usr/bin/env bash
set -e

# ==============================================================================
# IOI AI — Hugging Face Space Production Entrypoint
# Default Space Port: 7860
# ==============================================================================

PORT="${PORT:-7860}"
HOST="${HOST:-0.0.0.0}"

echo "=========================================="
echo "Starting IOI AI RAG Service on HF Space"
echo "Host: ${HOST} | Port: ${PORT}"
echo "Embedding Provider: ${EMBEDDING_PROVIDER:-sentence-transformers}"
echo "LLM Provider:       ${LLM_PROVIDER:-huggingface}"
echo "=========================================="

exec uvicorn app.main:app --host "$HOST" --port "$PORT"
