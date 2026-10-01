# RAG Service

Python-based Retrieval-Augmented Generation service for IOI AI.

## Current Status

**Foundation phase** — minimal HTTP server with a health-check endpoint. No RAG pipeline implemented yet.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

## Run

```bash
python -m app.main
# → http://localhost:8000
```

## Verify

```bash
curl http://localhost:8000/health
# → {"status": "ok", "service": "ioi-ai-rag-service"}
```

## Planned

- Embedding generation
- Vector store integration
- Document retrieval & reranking
- LLM integration
- FastAPI migration
\]\