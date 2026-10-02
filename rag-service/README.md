---
title: IOI AI RAG Service
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# IOI AI — Retrieval-Augmented Generation (RAG) Service

Production-ready, provider-agnostic Retrieval-Augmented Generation (RAG) microservice for the PW Institute of Innovation (PW IOI) School of Technology student directory.

---

## 🚀 Overview

The RAG service handles intelligent natural language queries, document retrieval, and grounded answer generation across 1,097 student directory records.

- **Intelligent Query Router**: Deterministic classification into Structured, Semantic, Hybrid, Aggregation, and Unsupported queries.
- **Provider-Agnostic LLM Layer**: Supports local Ollama (`llama3.2:1b`) for development and Hugging Face Serverless Inference API (`Llama-3.2-1B-Instruct`) for cloud deployment.
- **Dual Vector Store Support**: Compatible with FastEmbed (`BAAI/bge-small-en-v1.5`) and Sentence-Transformers (`all-MiniLM-L6-v2`) dense 384-dimensional embeddings.
- **FastAPI HTTP Service**: High-performance asynchronous API endpoints with telemetry logging and latency metrics.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` or `/health` or `/api/health` | Health check (ChromaDB status, record count, and LLM readiness) |
| `POST` | `/api/rag/query` | Natural-language query execution with source citations and timings |
| `GET` | `/api/metrics` | Recent query execution telemetry logs |
| `GET` | `/api/metrics/summary` | Aggregated latency percentiles (P50, P95) and query type distribution |

### Example Query Request
```bash
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Who are some students from Bengaluru?", "top_k": 5}'
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Default (Local) | Cloud / HF Spaces Value | Description |
|---|---|---|---|
| `PORT` | `8000` | `7860` | HTTP listening port |
| `HOST` | `0.0.0.0` | `0.0.0.0` | Bind host address |
| `LLM_PROVIDER` | `ollama` | `huggingface` | LLM generation runtime |
| `HF_TOKEN` | *None* | `hf_xxxxxxxxxxxxxxxx` | Hugging Face User Access Token (Required for cloud LLM) |
| `HF_MODEL` | `meta-llama/Llama-3.2-1B-Instruct` | `meta-llama/Llama-3.2-1B-Instruct` | Target Hugging Face inference model |
| `EMBEDDING_PROVIDER`| `fastembed` | `sentence-transformers` | Embedding model library |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | `sentence-transformers/all-MiniLM-L6-v2` | Dense embedding model tag |
| `VECTOR_STORE_PATH` | `../data/vectorstore` | `/home/user/app/data/vectorstore_hf` | Path to persistent ChromaDB index |
| `CORS_ORIGIN` | `*` | `*` | Allowed CORS origins |

---

## 🛠️ Local Development Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment configuration
cp .env.example .env

# 4. Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🐳 Docker & Hugging Face Spaces Deployment

This repository includes a production Dockerfile configured for Hugging Face Spaces (UID 1000, port 7860):

```bash
# Build Docker image
docker build -t ioi-ai-rag-service .

# Run container
docker run -p 7860:7860 \
  -e LLM_PROVIDER=huggingface \
  -e HF_TOKEN=your_hf_token \
  -e EMBEDDING_PROVIDER=sentence-transformers \
  ioi-ai-rag-service
```

For complete multi-tier deployment instructions across Hugging Face Spaces, Render, and Vercel, refer to [`docs/DEPLOYMENT_GUIDE.md`](../docs/DEPLOYMENT_GUIDE.md).