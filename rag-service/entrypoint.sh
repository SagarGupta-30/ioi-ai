#!/usr/bin/env bash
set -e

# Production deployment entrypoint for Hugging Face Spaces Docker
# Configures defaults suitable for port 7860 and sentence-transformers MiniLM vectorstore

export PORT="${PORT:-7860}"
export HOST="${HOST:-0.0.0.0}"
export EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-sentence-transformers}"
export EMBEDDING_MODEL="${EMBEDDING_MODEL:-sentence-transformers/all-MiniLM-L6-v2}"
export VECTOR_STORE_PATH="${VECTOR_STORE_PATH:-/home/user/app/data/vectorstore_hf}"
export LLM_PROVIDER="${LLM_PROVIDER:-huggingface}"
export HF_MODEL="${HF_MODEL:-meta-llama/Llama-3.2-1B-Instruct}"

echo "========================================================"
echo " Starting IOI AI RAG Service (Hugging Face Spaces)"
echo " Host:               ${HOST}"
echo " Port:               ${PORT}"
echo " LLM Provider:       ${LLM_PROVIDER}"
echo " LLM Model:          ${HF_MODEL}"
echo " Embedding Provider: ${EMBEDDING_PROVIDER}"
echo " Embedding Model:    ${EMBEDDING_MODEL}"
echo " Vector Store Path:  ${VECTOR_STORE_PATH}"
echo " HF_TOKEN Set:       $([ -n "${HF_TOKEN}" ] && echo "YES" || echo "NO")"
echo " MONGODB_URI Set:    $([ -n "${MONGODB_URI}" ] && echo "YES" || echo "NO")"
echo "========================================================"

exec python -m uvicorn app.main:app --host "${HOST}" --port "${PORT}"
