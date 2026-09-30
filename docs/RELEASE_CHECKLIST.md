# IOI AI — Step 8N.4 Final Release Checklist

Pre-deployment verification checklist for the IOI AI RAG knowledge assistant platform.
Every checkbox must be confirmed before production deployment or release sign-off.

---

## 1. Security & Configuration Verification

- [x] **Secrets audit**: Verified that zero database passwords, API tokens, or private credentials are committed to source control.
- [x] **Environment configuration**: Validated all `.env.example` templates (`rag-service`, `backend`, `frontend`) with clear distinction of required vs optional variables and production values.
- [x] **.gitignore verification**: Verified `.env`, `.env.local`, `data/vectorstore/`, `data/metrics/`, `logs/`, and build artifacts are ignored.
- [x] **Proxy isolation**: Verified browser clients communicate exclusively through Express (`:5001`). No direct browser access to FastAPI (`:8000`), MongoDB, or Ollama (`:11434`).
- [x] **Request size & bounds**: Enforced `1mb` body parser limit in Express and `1,000` character cap on query strings in both Express and FastAPI.

---

## 2. Compilation & Build Verification

- [x] **Backend build**: `cd backend && npm run build` compiled clean with 0 TypeScript errors.
- [x] **Frontend build**: `cd frontend && npm run build` successfully compiled 4 optimized static pages with 0 errors.
- [x] **Python import validation**: All core RAG modules (`embeddings`, `vector_store`, `retriever`, `generator`, `query_router`, `metrics`) imported cleanly.
- [x] **start.sh syntax**: `bash -n start.sh` passed with 0 syntax errors.

---

## 3. Automated Test Suite & Regression

- [x] **Metrics tests**: `cd rag-service && python3 -m app.scripts.test_metrics` (4/4 tests passed).
- [x] **Query router tests**: `cd rag-service && python3 -m app.scripts.test_query_router` (9/9 test queries passed).
- [x] **Retrieval evaluation**: `cd rag-service && python3 -m app.scripts.evaluate_retrieval` (10/10 queries evaluated, avg retrieval 36.43ms).
- [x] **RAG evaluation**: `cd rag-service && python3 -m app.scripts.evaluate_rag` (7/7 test cases passed, 100% grounded answers).
- [x] **FastAPI tests**: `cd rag-service && python3 -m app.scripts.test_api` (4/4 API schema & boundary tests passed).
- [x] **Step 8K evaluation**: `cd rag-service && python3 -m app.scripts.evaluate_step_8k` (22/22 queries passed across 6 categories, 0 grounding/safety failures).
- [x] **Backend proxy tests**: `cd backend && npm run test:rag` (6/6 proxy, validation, error handling, and metrics tests passed).

---

## 4. Startup & Runtime Readiness

- [x] **Startup check**: `./start.sh --check-only` successfully verified all binaries, directories, ChromaDB data, and environment files.
- [x] **End-to-end smoke test**: `./start.sh --smoke-test` verified complete pipeline (`Client → Express → FastAPI → ChromaDB → Ollama`) with HTTP 200.
- [x] **Health verification**: Verified all 4 service health endpoints (`http://localhost:8000/api/health`, `http://localhost:11434/api/tags`, `http://localhost:5001/api/health`, `http://localhost:3000`).
- [x] **Frontend browser verification**: Verified Next.js UI connects to backend proxy, supports search, and renders both RAG Assistant and Observability Dashboard.
- [x] **README review**: Verified `README.md` includes comprehensive architecture, one-command startup, API reference, test suite, security, and Deployment & Release Guide.

---

## 5. Deployment Environment Notice

> **IMPORTANT:** IOI AI utilizes a **100% free, local** inference architecture.
> - FastEmbed operates locally via ONNX Runtime (`BAAI/bge-small-en-v1.5`).
> - ChromaDB operates as an embedded local persistent vector database.
> - Ollama runs locally on `localhost:11434` with `llama3.2:1b`.
> Deployment targets (e.g. servers, VMs, or private cloud nodes) must provide host hardware capable of running Ollama locally if local generation is preserved.
