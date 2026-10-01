# IOI AI — PW Institute of Innovation Knowledge Assistant

An end-to-end, privacy-conscious, **100% free and local** Retrieval-Augmented Generation (RAG) knowledge assistant for the PW Institute of Innovation (PW IOI) School of Technology.

> **Data Disclosure & Privacy Notice:**
> This project operates exclusively on publicly accessible student directory listings (1,096 records from PW IOI School of Technology) alongside explicitly tagged synthetic demo profiles (1 demo record with sample project/skill details). No private contact information, academic grades, or sensitive student records are stored or exposed.

---

## Architecture Overview

IOI AI is built on a decoupled, production-hardened multi-tier architecture featuring an **Intelligent Query Router and Hybrid Retrieval Engine**. It supports two execution environments:

### 1. Cloud Production Architecture
```
[ Next.js Frontend ] (Hosted on Vercel)
        │
        ▼ HTTPS REST (NEXT_PUBLIC_API_URL)
[ Node/Express Backend Proxy ] (Hosted on Render Web Service)
   ├── MongoDB Atlas (Student Directory REST CRUD)
   └── Validates query parameters & timeouts
        │
        ▼ HTTPS REST (RAG_SERVICE_URL)
[ Python FastAPI RAG Service ] (Hosted on Hugging Face Spaces / Docker)
   ├── Intelligent Query Router (Deterministic Rule & Regex Classifier)
   ├── Sentence-Transformers (all-MiniLM-L6-v2 — 384-dim dense vectors)
   ├── ChromaDB Vector Store (data/vectorstore_hf — 1,097 records)
   └── Cloud LLM Inference (Hugging Face Serverless API — Llama-3.2-1B-Instruct)
```

### 2. Local Development Architecture
```
[ Next.js Frontend ] (Port 3000)
        │
        ▼ HTTP REST / JSON
[ Node/Express Backend Proxy ] (Port 5001)
   ├── MongoDB Atlas (Student Directory REST CRUD)
   └── Validates query parameters & timeouts
        │
        ▼ HTTP REST / JSON
[ Python FastAPI RAG Service ] (Port 8000)
   ├── Intelligent Query Router (app/query_router.py)
   │         │
   │         ▼ (Deterministic Classification)
   │    ┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
   │    ▼              ▼              ▼              ▼              ▼              ▼
   │ [STRUCTURED]   [SEMANTIC]     [HYBRID]       [AGGREGATION]  [UNSUPPORTED]
   │  ChromaDB       FastEmbed      Metadata pre-   MongoDB Atlas  Deterministic
   │  Metadata       HNSW Cosine    filter + Dense  Direct Count   Safe Refusal
   │  Filter + LLM   Search + LLM   Rank + LLM      (No LLM)       (No LLM)
   │
   ├── FastEmbed (BAAI/bge-small-en-v1.5 — 384-dim dense vectors)
   ├── ChromaDB Persistent Vector Store (data/vectorstore/)
   └── Local Ollama LLM (llama3.2:1b @ Port 11434)
```

---

## Intelligent Query Routing & Hybrid Retrieval (Step 8J)

Incoming natural-language queries are classified **deterministically** using rule-based Python logic (zero LLM overhead, zero cloud dependencies) into one of five execution pipelines:

### 1. STRUCTURED Queries
- **Trigger:** Queries with exact directory constraints (campus, batch, gender, school) without semantic topical keywords.
- **Example:** `"male students from batch 26"`, `"female students from Pune"`
- **Execution Path:** Converts constraints directly to ChromaDB metadata filters (`where={"$and": [{"gender": "MALE"}, {"batch": "26"}]}`). Vector distance ranks matching candidates, guaranteeing 100% constraint satisfaction.

### 2. SEMANTIC Queries
- **Trigger:** Free-form questions about interests, skills, or specific students without explicit metadata constraints.
- **Example:** `"students interested in artificial intelligence"`, `"tell me about Aarushi Mandloi"`
- **Execution Path:** FastEmbed query embedding (384 dimensions) → ChromaDB HNSW cosine similarity search → top-K context assembly → Ollama answer generation.

### 3. HYBRID Queries
- **Trigger:** Queries combining structured metadata constraints with specific topical/semantic search terms.
- **Example:** `"female students from Pune interested in machine learning"`
- **Execution Path:**
  1. Metadata pre-filtering narrows candidates to exact criteria (`campus="Pune"`, `gender="FEMALE"`).
  2. Isolates the topical search string (`"machine learning"`).
  3. Computes dense vector similarity against the pre-filtered subset.
  4. Ollama generates an answer grounded strictly on the hybrid results.

### 4. AGGREGATION Queries
- **Trigger:** Inquiries requesting total counts, student numbers, or institutional demographic statistics.
- **Example:** `"how many students are in Bengaluru?"`, `"how many male students are there?"`
- **Execution Path:**
  1. Safe read-only count query directly against MongoDB Atlas (`db.students.count_documents(...)`).
  2. **Bypasses ChromaDB vector search and LLM generation completely.**
  3. Returns instant exact numerical results (`~39 ms` latency, **108x faster** than full RAG generation).
  4. Structured response contains both a human-readable sentence and a machine-readable count payload:
     ```json
     {
       "type": "aggregation",
       "result": { "count": 453 }
     }
     ```

### 5. UNSUPPORTED Queries
- **Trigger:** Requests for private, sensitive, or non-existent attributes (phone numbers, personal emails, residential addresses, CGPA, exam grades, salary/stipend).
- **Example:** `"what is Aarushi Mandloi's phone number?"`, `"what is Priya Sharma's CGPA?"`
- **Execution Path:**
  1. Deterministic guardrail intercepts the query instantly (`~16 ms`).
  2. Refuses the private request without invoking hallucination-prone LLM calls.
  3. If a student is named, retrieves their public directory card for helpfulness while explicitly declining the private attribute.

---

## Technology Stack

| Layer | Component | Local Specification | Cloud / Production Specification |
|---|---|---|---|
| **Frontend** | Next.js 16 (App Router) + Tailwind CSS | Port `3000` (`npm run dev`) | **Vercel** (`frontend/vercel.json`) |
| **Backend API** | Node.js + Express + TypeScript | Port `5001` (`npm run dev`) | **Render Web Service** (`render.yaml`) |
| **Primary DB** | MongoDB Atlas (`ioi_ai.students`) | 1,097 documents | MongoDB Atlas Production Cluster |
| **RAG Service** | Python 3.12 + FastAPI + Uvicorn | Port `8000` | **Hugging Face Spaces** (Docker, Port `7860`) |
| **Query Router** | Deterministic Regex & Rule Classifier | `app/query_router.py` | `app/query_router.py` (Rule-based) |
| **Embeddings** | FastEmbed / Sentence-Transformers | FastEmbed (`BAAI/bge-small-en-v1.5`, 384d) | Sentence-Transformers (`all-MiniLM-L6-v2`, 384d) |
| **Vector Store** | ChromaDB (`PersistentClient`) | `data/vectorstore/` (BGE index) | `data/vectorstore_hf/` (MiniLM index) |
| **LLM Runtime** | Configurable (`LLM_PROVIDER`) | Ollama (`llama3.2:1b` @ Port 11434) | Hugging Face Serverless Inference API (`Llama-3.2-1B-Instruct`) |

---

## Required Services & Ports

Ensure the following local services are active before running queries:

| Service | Port | Status Check Command |
|---|---|---|
| **Ollama** | `11434` | `curl http://localhost:11434/api/tags` |
| **FastAPI RAG Service** | `8000` | `curl http://localhost:8000/api/health` |
| **Node/Express Backend** | `5001` | `curl http://localhost:5001/api/health` |
| **Next.js Frontend** | `3000` | Open `http://localhost:3000` in browser |

---

## Environment Variables

### 1. Backend (`backend/.env`)
```env
PORT=5001
CORS_ORIGIN=*
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/ioi_ai
MONGODB_DATABASE=ioi_ai
RAG_SERVICE_URL=http://localhost:8000
```

### 2. RAG Service (`rag-service/.env`)
```env
PORT=8000
CORS_ORIGIN=*
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/ioi_ai
MONGODB_DATABASE=ioi_ai
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
VECTOR_STORE_PATH=../data/vectorstore
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
OLLAMA_TIMEOUT_SECONDS=120
```

### 3. Frontend (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:5001
```

---

## One-Command Local Startup (Step 8N.2)

To start and verify the entire IOI AI RAG stack with a single command:

```bash
./start.sh
```

### What the Script Starts & Verifies:
1. **Pre-flight Checks:** Verifies `python3`, `node`, `npm`, `ollama`, directory structures, dependencies, ChromaDB vector store data (`chroma.sqlite3`), and `.env` configuration files.
2. **Ollama LLM Runtime (`11434`):** Verifies connection and ensures `llama3.2:1b` is installed. Starts Ollama automatically on macOS if offline.
3. **FastAPI RAG Service (`8000`):** Checks port `8000`. Detects and reuses compatible existing instances or spawns `uvicorn app.main:app` and polls `/api/health`.
4. **Node/Express Backend (`5001`):** Checks port `5001`. Reuses or spawns `npm run dev` and polls `/api/health`.
5. **Next.js Frontend (`3000`):** Checks port `3000`. Reuses or spawns `npm run dev` and polls for HTTP 200 readiness.
6. **Automated Smoke Test:** Executes an end-to-end RAG query test via the public Express proxy (`POST /api/rag/query`) to verify `Frontend → Express → FastAPI → ChromaDB → Ollama`.
7. **Clean Shutdown:** Captures `SIGINT` / `SIGTERM` (`Ctrl+C`) and gracefully terminates all services spawned by the script.

### Service Ports & URLs:
| Service | Port | Status / Health URL |
|---|---|---|
| **Ollama** | `11434` | `http://localhost:11434/api/tags` |
| **FastAPI RAG** | `8000` | `http://localhost:8000/api/health` |
| **Node/Express** | `5001` | `http://localhost:5001/api/health` |
| **Next.js Frontend** | `3000` | `http://localhost:3000` |

### Where Logs Are Stored:
All service outputs are streamed directly to the local `logs/` directory (git-ignored):
- `logs/ollama.log`
- `logs/rag-service.log`
- `logs/backend.log`
- `logs/frontend.log`

### How to Stop Everything:
Press **`Ctrl+C`** in the terminal running `./start.sh`. The script safely terminates all child services it started. Existing external processes are not touched.

### Command-Line Flags:
```bash
./start.sh               # Standard startup, smoke test, and active monitor
./start.sh --check-only   # Validate pre-flight checks and exit immediately
./start.sh --smoke-test   # Run end-to-end RAG verification test and exit immediately
```

### Troubleshooting:
- **Port blocked by incompatible process:** Identify the PID with `lsof -nP -i :<PORT> -sTCP:LISTEN` and terminate it before starting.
- **Missing Ollama model:** Run `ollama pull llama3.2:1b`.
- **Missing vector store:** Re-index by running `cd rag-service && python3 -m app.scripts.build_vector_store`.
- **Missing Python packages:** Run `cd rag-service && pip install -r requirements.txt`.
- **Missing Node packages:** Run `cd backend && npm install && cd ../frontend && npm install`.

---

## Step-by-Step Setup Guide

### 1. Install & Start Ollama
```bash
# macOS (Homebrew)
brew install ollama
brew services start ollama

# Pull the lightweight 1B model
ollama pull llama3.2:1b
```

### 2. Setup Python RAG Service
```bash
cd rag-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Build RAG Pipeline Data & Indexes
Run these commands sequentially from `rag-service/`:

```bash
# Step 8A: Generate normalized student documents from MongoDB Atlas
python3 -m app.scripts.build_documents

# Step 8B: Generate 384-dimensional dense vectors via FastEmbed
python3 -m app.scripts.generate_embeddings

# Step 8C: Build local ChromaDB persistent index
python3 -m app.scripts.build_vector_store
```

### 4. Start the Application Services

**Terminal 1 — FastAPI RAG Service:**
```bash
cd rag-service
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Node/Express Backend:**
```bash
cd backend
npm install
npm run dev
```

**Terminal 3 — Next.js Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Visit **`http://localhost:3000`** in your browser.

---

## Evaluation & Benchmarks

The RAG service includes automated quality and latency evaluation suites:

### 1. Query Router & Hybrid Suite (`app/scripts/test_query_router.py`)
```bash
cd rag-service
python3 -m app.scripts.test_query_router
```
- **Test Pass Rate:** **9 / 9 (100%)**
- Verifies classification and execution for Structured, Semantic, Hybrid, Aggregation, and Unsupported queries.

### 2. Step 8J Latency Comparison Benchmark (`app/scripts/benchmark_router_latency.py`)
```bash
cd rag-service
python3 -m app.scripts.benchmark_router_latency
```

| Query Category | Step 8J Latency | Step 8I Baseline | Improvement |
|---|:---:|:---:|:---:|
| **AGGREGATION** | **39.1 ms** | 4.23 s | **108.0x faster** (Direct MongoDB Atlas count) |
| **UNSUPPORTED** | **16.1 ms** | 2.36 s | **146.9x faster** (Deterministic safety guardrail) |
| **STRUCTURED** | **7.13 s** | 4.03 s | Exact metadata filtering + Ollama generation |
| **SEMANTIC** | **11.40 s** | 4.96 s | Dense vector retrieval + Ollama generation |
| **HYBRID** | **14.46 s** | 4.75 s | Metadata pre-filtering + dense ranking + Ollama |

---

## API Examples

### 1. Health Check
```bash
curl http://localhost:8000/api/health
```

### 2. Hybrid Query Example
```bash
curl -X POST http://localhost:5001/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "female students from Pune interested in machine learning",
    "top_k": 3
  }'
```
**Response:**
```json
{
  "success": true,
  "query": "female students from Pune interested in machine learning",
  "query_type": "hybrid",
  "answer": "Based on the retrieved student records, the female students from Pune interested in machine learning are:\n\n1. KUMKUM JANGIR (Pune, Batch 25, FEMALE)\n2. KHUSHI AGARWAL (Pune, Batch 25, FEMALE)\n3. AYESHA SHEIKH (Pune, Batch 25, FEMALE)",
  "sources": [
    {
      "student_id": "847242ba-...",
      "name": "KUMKUM JANGIR",
      "campus": "Pune",
      "batch": "25",
      "gender": "FEMALE",
      "similarity_score": 0.5821,
      "source_type": "pwioi_public_api"
    }
  ]
}
```

### 3. Aggregation Query Example
```bash
curl -X POST http://localhost:5001/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how many students are in Bengaluru?"
  }'
```
**Response:**
```json
{
  "success": true,
  "query": "how many students are in Bengaluru?",
  "query_type": "aggregation",
  "retrieval_status": "not_applicable",
  "answer": "According to the PW IOI student directory, there are **453 students at Bengaluru campus**.",
  "sources": [],
  "aggregation": {
    "count": 453,
    "filters": {
      "campus": "Bengaluru"
    }
  },
  "timings": {
    "classification_ms": 0.4,
    "aggregation_ms": 32.1,
    "total_ms": 32.5
  }
}
```

---

## Step 8K — Production Hardening & Evaluation Layer

Step 8K introduces a comprehensive production-hardening, quality-assurance, and evaluation layer across the retrieval, generation, and API proxy pipelines.

### 1. Configurable Retrieval Settings & Thresholds

Retrieval parameters are calibrated and exposed via environment variables:

| Setting | Env Variable | Default | Max | Description |
|---|---|---|---|---|
| Default Top K | `TOP_K_DEFAULT` | `5` | `50` | Default number of ranked records retrieved |
| Max Top K | `TOP_K_MAX` | `50` | `50` | Hard cap preventing excessive memory / context expansion |
| Cosine Threshold | `SIMILARITY_THRESHOLD` | `0.58` | `1.0` | Minimum cosine similarity required to pass context to LLM |

**Threshold Calibration & Rationale:**
- Tested across FastEmbed `BAAI/bge-small-en-v1.5` embeddings on 1,097 documents.
- Relevant student directory queries achieve cosine similarities of `0.65 – 0.80` (e.g. *"Tell me about Aarushi Mandloi"* scores `0.6576`).
- Weak, ambiguous, or out-of-domain queries achieve similarities of `0.44 – 0.55` (e.g. *"weather today"* = `0.5288`, *"write me a poem"* = `0.5502`, *"capital of France"* = `0.4605`).
- A calibrated cutoff of `0.58` cleanly suppresses noise and unrelated prompts without dropping legitimate student directory queries.

---

### 2. Failure State Taxonomies & Explicit Handling

IOI AI distinguishes between five distinct operational conditions:

```
┌─────────────────────────┬─────────────────────────────────────────────────────────────────────────────┐
│ Failure / Status Type   │ Definition & System Behavior                                                │
├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 1. Insufficient Evidence│ Context found in ChromaDB, but all similarity scores fall below 0.58.       │
│    (insufficient_results) Bypasses Ollama generation deterministically. Returns standard refusal.    │
├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2. Retrieval Failure    │ Vector search / MongoDB filter returned 0 matching records.                  │
│    (no_results)         Bypasses Ollama generation deterministically. Returns explicit empty message. │
├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 3. Unsupported Query    │ Request asks for private, unrecorded attributes (phone, email, CGPA, etc.). │
│    (not_applicable)     Intercepted in ~16ms by deterministic regex guardrail without LLM inference.  │
├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 4. Generation Failure   │ Ollama timeout, memory error, or context formatting parsing exception.       │
│                         Caught by exception boundary; returns structured HTTP 500 error payload.      │
├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 5. Service Unavailable  │ FastAPI RAG service or Ollama runtime offline or unreachable.              │
│                         Caught by Express proxy; returns clean HTTP 503 RAGServiceError to client.    │
└─────────────────────────┴─────────────────────────────────────────────────────────────────────────────┘
```

**Deterministic Insufficient Results Response:**
```json
{
  "success": true,
  "query": "write me a poem",
  "query_type": "out_of_domain",
  "retrieval_status": "insufficient_results",
  "answer": "I couldn't find sufficiently relevant information in the available student records. IOI AI is a specialized assistant dedicated to the PW Institute of Innovation student directory.",
  "sources": [],
  "timings": {
    "classification_ms": 0.2,
    "total_ms": 0.4
  }
}
```

---

### 3. Grounding Guardrails & Privacy Protections

1. **Strict Context Gating:** LLM prompt instructions strictly mandate using only facts in the retrieved context block.
2. **Sanitized Prompt Headers:** Internal technical UUIDs are removed from prompt context blocks (`[Student Record 1]` instead of `[Document 1 | ID: <uuid>]`). This prevents smaller local models (e.g. `llama3.2:1b`) from regurgitating raw database keys.
3. **No Attribute Hallucination:** The LLM is explicitly forbidden from inventing phone numbers, email addresses, CGPAs, grades, or unrecorded projects.
4. **Missing Value Transparency:** Missing attributes (`"Not available"`) are explicitly treated as unavailable data rather than converted into factual claims.

---

### 4. Granular Performance Instrumentation

Every stage of query processing is measured in milliseconds:
- `classification_ms`: Query router rule classification
- `embedding_ms`: FastEmbed query dense vector generation
- `retrieval_ms`: ChromaDB HNSW cosine similarity search
- `aggregation_ms`: MongoDB count execution (for count queries)
- `context_ms`: Document string formatting and prompt assembly
- `generation_ms`: Local Ollama inference latency
- `total_ms`: End-to-end request duration

Timings are exposed in `timings: {}` in the API response without leaking server infrastructure details to the UI.

---

### 5. Automated Regression & Evaluation Commands

Run the full evaluation and regression suites:

```bash
# Step 8K: 22-query comprehensive evaluation across all 6 query categories
cd rag-service
python3 -m app.scripts.evaluate_step_8k

# Step 8J: Query router & hybrid retrieval regression
python3 -m app.scripts.test_query_router

# Step 8I: Retrieval quality & cosine similarity evaluation
python3 -m app.scripts.evaluate_retrieval

# Step 8I: End-to-end grounded generation evaluation
python3 -m app.scripts.evaluate_rag

# Step 8F: FastAPI schema validation tests
python3 -m app.scripts.test_api

# Step 8G: Backend Express proxy tests & build
cd ../backend
npm run test:rag
npm run build

# Step 8H: Frontend Next.js production build
cd ../frontend
npm run build
```

---

### 6. Actual Measured Benchmark Results (Step 8K Evaluation)

```text
==================================================
STEP 8K EVALUATION SUMMARY
==================================================
Total queries:          22
Passed:                 22 / 22 (100.0%)
Failed:                 0

Structured:             4 / 4 (100%)
Semantic:               4 / 4 (100%)
Hybrid:                 2 / 2 (100%)
Aggregation:            4 / 4 (100%)
Unsupported:            5 / 5 (100%)
Out-of-domain:          3 / 3 (100%)

Average latency:        2,833.9 ms
P95 latency:            7,499.2 ms

Grounding failures:     0
Safety failures:        0
==================================================
```

**Per-Category Latency Breakdown:**
- **Out-of-Domain / Weak Retrieval:** `< 1 ms` (short-circuited before Ollama)
- **Unsupported Private Attributes:** `0 – 35 ms` (deterministic regex rejection)
- **Aggregation Count Queries:** `30 – 827 ms` (direct MongoDB count index)
- **Full RAG Generation (LLM):** `3,391 – 9,109 ms` (Ollama `llama3.2:1b` on Apple Silicon)

---

### 7. Remaining Limitations

1. **Local 1B Parameter Capacity:** `llama3.2:1b` is optimized for low memory footprints (~1.3 GB RAM) and fast local inference. Complex multi-step reasoning or lengthy multi-student comparisons can occasionally exhibit repetition or brief omissions if prompts become overly convoluted.
2. **Aggregation Specificity:** Fast aggregations are supported for exact metadata dimensions (Campus, Batch, Gender, School). Aggregations over open-ended semantic concepts (e.g. *"how many students like robotics?"*) require approximate nearest-neighbor clustering or complete embeddings scan.
3. **Public Directory Information Scope:** 1,096 of the records are derived from public institutional directories. Missing contact info and academic performance are by design and strictly safeguarded against false claims.

---

## Step 8L — Production Observability & Evaluation Dashboard

Step 8L adds a production-grade observability, telemetry, and evaluation dashboard layer to IOI AI without introducing any paid or cloud-hosted monitoring dependencies (100% free and local).

### 1. Observability Architecture

```
[ Next.js Observability Dashboard ] (Port 3000)
    │
    ▼ HTTP GET /api/rag/metrics & /api/rag/metrics/summary (Auto-refresh every 8s)
[ Node/Express Backend Proxy ] (Port 5001)
    │
    ▼ HTTP GET /api/metrics & /api/metrics/summary
[ Python FastAPI Service ] (Port 8000)
    │
    ▼ app/metrics.py (MetricsCollector)
    ├── Thread-Safe Circular In-Memory Buffer (up to 1,000 queries)
    └── Local JSONL Persistence: data/metrics/query_metrics.jsonl
```

### 2. Endpoints & Schemas

#### `GET /api/metrics/summary` (Aggregated Telemetry)
Available at `http://localhost:5001/api/rag/metrics/summary` (Express proxy) and `http://localhost:8000/api/metrics/summary` (FastAPI).

**Sample Response:**
```json
{
  "success": true,
  "summary": {
    "total_queries": 22,
    "successful_queries": 22,
    "failed_queries": 0,
    "success_rate_pct": 100.0,
    "query_type_distribution": {
      "structured": 4,
      "semantic": 4,
      "hybrid": 2,
      "aggregation": 4,
      "unsupported": 5,
      "out_of_domain": 3
    },
    "retrieval_status_distribution": {
      "sufficient": 10,
      "insufficient_results": 3,
      "not_applicable": 9
    },
    "latency_stats": {
      "avg_total_ms": 2139.9,
      "min_total_ms": 0.2,
      "max_total_ms": 7388.5,
      "p50_total_ms": 1850.0,
      "p95_total_ms": 5512.8,
      "avg_classification_ms": 0.5,
      "avg_embedding_ms": 4.8,
      "avg_retrieval_ms": 18.2,
      "avg_generation_ms": 4820.1,
      "avg_aggregation_ms": 42.5
    },
    "last_updated": "2026-09-30T10:30:00Z"
  }
}
```

#### `GET /api/metrics` (Raw Telemetry Log)
Available at `http://localhost:5001/api/rag/metrics?limit=30` and `http://localhost:8000/api/metrics?limit=30`.

**Query Parameters:**
* `limit`: Max records to return (1 – 200, default: 50)
* `query_type`: Optional filter (`structured`, `semantic`, `hybrid`, `aggregation`, `unsupported`, `out_of_domain`)
* `status`: Optional filter (`sufficient`, `insufficient_results`, `no_results`, `not_applicable`)

### 3. Frontend Dashboard Features

The Next.js frontend at `http://localhost:3000` includes a view switcher between the **Assistant** and **Observability** dashboard:
* **Real-time KPI Cards:** Total queries recorded, Success rate %, Mean total latency, and P95 latency.
* **Query Type Distribution:** Visual representation of queries handled across Structured, Semantic, Hybrid, Aggregation, Unsupported, and Out-of-Domain.
* **Pipeline Stage Latency Breakdown:** Latencies for Query Classification, Dense Vector Embedding, ChromaDB Retrieval, MongoDB Count Aggregation, and Ollama Generation.
* **Retrieval Evidence Status Cards:** Counters for Sufficient Context, Insufficient Evidence, No Records Found, and Direct/Guardrail.
* **Recent Query Telemetry Log:** Searchable, scrollable audit table with timestamps, query strings, pipeline classifications, retrieval statuses, source counts, and total execution latencies.
* **Auto-refresh toggle:** Periodic 8-second polling with manual refresh option.

### 4. Verification & Automated Test Commands

```bash
# Test Step 8L Metrics Collection and Endpoints
cd rag-service
python3 -m app.scripts.test_metrics

# Run full evaluation & regression suites
python3 -m app.scripts.evaluate_step_8k
python3 -m app.scripts.test_query_router
python3 -m app.scripts.evaluate_retrieval
python3 -m app.scripts.evaluate_rag
python3 -m app.scripts.test_api

# Run Performance Benchmark Suite (Step 8N.3)
python3 -m app.scripts.benchmark_production_performance

# Run Backend Tests (includes metrics proxy tests) & Build
cd ../backend
npm run test:rag
npm run build

# Run Frontend Production Build
cd ../frontend
npm run build

# Verify Startup Automation
cd ..
bash -n start.sh
./start.sh --check-only
./start.sh --smoke-test
```

---

## Step 8N.3 — Production Hardening & Final System Verification

Step 8N.3 represents the finalized, production-hardened verification of the entire IOI AI RAG platform.

### 1. Hardened Production Architecture

```
[ Browser / User ]
        │
        ▼ HTTP REST / JSON (Only entry point)
[ Next.js Frontend ] (Port 3000)
        │
        ▼ Proxied via process.env.NEXT_PUBLIC_API_URL
[ Node/Express Backend Proxy ] (Port 5001)
   ├── Body limit: 1MB (Memory exhaustion DoS prevention)
   ├── Query validation: Non-empty, max 1,000 characters
   ├── Parameter bounds: top_k (1–50)
   ├── Error boundary: Sanitized client error messages (no stack traces)
   └── MongoDB Atlas: Direct demographic aggregations (db.students)
        │
        ▼ Internal HTTP REST (Protected network)
[ Python FastAPI RAG Service ] (Port 8000)
   ├── Input Schema: Pydantic RAGQueryRequest (max_length=1000)
   ├── Query Router: Deterministic classification (Structured, Semantic, Hybrid, Aggregation, Unsupported, Out-of-Domain)
   ├── Error Sanitization: Server-side logging, generic client errors
   ├── Embeddings: FastEmbed BAAI/bge-small-en-v1.5 (384 dims, local ONNX)
   ├── Vector Store: ChromaDB HNSW Cosine Index (1,097 records)
   └── LLM Runtime: Local Ollama (llama3.2:1b @ Port 11434, 120s timeout)
```

### 2. Security Considerations & Protections

1. **Proxy Isolation:** Browser clients communicate **exclusively** with the Node/Express backend (`:5001`). No browser traffic ever touches FastAPI (`:8000`), MongoDB Atlas, or Ollama (`:11434`) directly.
2. **Payload Protection:** Express body parser enforces a strict `1MB` ceiling (`express.json({ limit: "1mb" })`) to prevent heap exhaustion.
3. **Query Length Bounds:** Natural-language queries are capped at `1,000` characters in both Express and FastAPI Pydantic schemas, blocking buffer abuse and runaway embedding workloads.
4. **Information Leakage Prevention:** Internal Python stack traces, MongoDB connection URIs, and local file paths are intercepted and logged server-side only; callers receive clean, sanitized HTTP status responses.
5. **Secret Hygiene:** All credentials (`MONGODB_URI`, optional `OPENAI_API_KEY`) reside strictly in git-ignored `.env` files. Templates use placeholders (`<user>:<password>`).
6. **Privacy Guardrails:** Personal phone numbers, emails, addresses, grades, and CGPA are deterministically rejected with standard refusal responses without invoking LLM generation.

### 3. API Endpoints Reference

| Method | Endpoint | Handler | Description |
|---|---|---|---|
| `GET` | `/api/health` | Backend / FastAPI | Service health, ChromaDB record count, and Ollama status |
| `POST` | `/api/rag/query` | Backend Proxy (`:5001`) | Primary RAG search & answer generation endpoint |
| `GET` | `/api/rag/metrics` | Backend Proxy (`:5001`) | Raw telemetry audit records with pagination & filters |
| `GET` | `/api/rag/metrics/summary` | Backend Proxy (`:5001`) | Aggregated performance, latency stats, and distributions |
| `GET` | `/api/students` | Backend (`:5001`) | Public student directory CRUD & search |

### 4. Performance Benchmark & Bottleneck Profile

Measured across 118+ production-like queries through the Express proxy on Apple Silicon:

| Stage | Typical Latency | % of Total Time | Architecture Notes |
|---|:---:|:---:|---|
| **Query Classification** | `< 1 ms` | `0.02%` | Rule-based regex & constraint parsing |
| **FastEmbed Embedding** | `5 – 50 ms` | `0.5%` | 384-dim dense vector generation via ONNX |
| **ChromaDB Vector Retrieval** | `15 – 35 ms` | `0.8%` | Local HNSW cosine similarity search |
| **MongoDB Count Aggregation** | `30 – 50 ms` | `1.0%` | Direct indexed query; bypasses vector & LLM |
| **Deterministic Guardrail** | `0.5 – 25 ms` | `0.4%` | Unsupported & Out-of-Domain short-circuit |
| **Ollama Token Generation** | `2,500 – 6,000 ms` | `> 95.0%` | **Primary bottleneck**: Local 1B model inference |

### 5. Final Verification Test Matrix

| Test Suite | Command | Test Cases | Pass Rate |
|---|---|:---:|:---:|
| **Metrics & Observability** | `python3 -m app.scripts.test_metrics` | 4 tests | **100%** (4/4) |
| **Query Router & Hybrid** | `python3 -m app.scripts.test_query_router` | 9 queries | **100%** (9/9) |
| **Retrieval Quality** | `python3 -m app.scripts.evaluate_retrieval` | 10 queries | **100%** (10/10) |
| **RAG Answer Generation** | `python3 -m app.scripts.evaluate_rag` | 7 cases | **100%** (7/7) |
| **FastAPI Layer Validation** | `python3 -m app.scripts.test_api` | 4 tests | **100%** (4/4) |
| **Comprehensive Step 8K** | `python3 -m app.scripts.evaluate_step_8k` | 22 queries | **100%** (22/22) |
| **Express Backend Proxy** | `cd backend && npm run test:rag` | 6 tests | **100%** (6/6) |
| **Backend TypeScript Build** | `cd backend && npm run build` | Full codebase | **0 errors** |
| **Frontend Production Build**| `cd frontend && npm run build` | 4 pages | **Compiled Clean** |
| **Startup Script Validation**| `bash -n start.sh` | Shell check | **0 errors** |
| **One-Command Pre-flight** | `./start.sh --check-only` | Environment & files | **Passed** |
| **End-to-End Smoke Test** | `./start.sh --smoke-test` | Express → Ollama | **Passed (HTTP 200)** |

### 6. Known Limitations

1. **Local LLM Token Generation:** Local CPU/Metal inference takes 2.5–6s per generation for complex answers. (Aggregation queries bypass this and finish in < 50ms).
2. **Directory Data Scope:** 1,096 public directory profiles contain basic school, campus, batch, and gender information. Only synthetic profiles contain sample skills/projects. Private contact info is intentionally unavailable and safeguarded.

---

## Deployment & Release Guide (Step 8N.4)

This guide provides everything needed to deploy, verify, and operate the IOI AI RAG knowledge assistant platform.

### 1. Architecture
IOI AI operates as a 4-tier decoupled local system:
- **Tier 1 (Frontend):** Next.js 16 (App Router) on Port `3000`. Exclusively sends queries to the Express backend proxy.
- **Tier 2 (Backend Proxy):** Node.js + Express + TypeScript on Port `5001`. Handles input validation, body limits (1MB), timeout management, and MongoDB Atlas demographic aggregations.
- **Tier 3 (RAG Service):** Python 3 + FastAPI on Port `8000`. Houses the deterministic Query Router, FastEmbed ONNX embedding generator, ChromaDB local vector store (1,097 records), and prompt formatting.
- **Tier 4 (LLM Runtime):** Local Ollama service on Port `11434` running `llama3.2:1b`.

> **CRITICAL LOCAL DEPLOYMENT REQUIREMENT:**
> Ollama runs **100% locally and free**. Deployment target environments (bare-metal, VMs, or private servers) must provide host CPU/GPU hardware capable of running Ollama and the `llama3.2:1b` model locally. The application does **not** rely on external OpenAI, Gemini, or paid cloud APIs.

### 2. Prerequisites
- **Operating System:** macOS (Apple Silicon recommended) or Linux (Ubuntu 22.04+ / Debian 12+)
- **Python:** 3.10+ (tested on Python 3.12 / 3.14)
- **Node.js:** 18+ (tested on Node v20+)
- **npm:** 9+
- **Ollama:** Installed with `llama3.2:1b` model pulled (`ollama pull llama3.2:1b`)
- **MongoDB Atlas:** Read-only access URI configured in `.env` files

### 3. Environment Variables

| Variable | Tier | Required | Default | Description |
|---|---|:---:|---|---|
| `PORT` | Backend | Optional | `5001` | HTTP port for Node/Express server |
| `CORS_ORIGIN` | Backend / RAG | Optional | `*` | Allowed CORS origins for API clients |
| `MONGODB_URI` | Backend / RAG | **Required** | None | MongoDB Atlas connection string |
| `MONGODB_DATABASE` | RAG Service | Optional | `ioi_ai` | Target MongoDB database name |
| `RAG_SERVICE_URL` | Backend | **Required** | `http://localhost:8000` | Internal FastAPI service endpoint |
| `NEXT_PUBLIC_API_URL`| Frontend | **Required** | `http://localhost:5001` | Public backend proxy endpoint |
| `LLM_PROVIDER` | RAG Service | Optional | `ollama` | Local LLM engine |
| `OLLAMA_BASE_URL` | RAG Service | Optional | `http://localhost:11434` | Ollama HTTP host |
| `OLLAMA_MODEL` | RAG Service | Optional | `llama3.2:1b` | Model tag |
| `OLLAMA_TIMEOUT_SECONDS` | RAG Service | Optional | `120` | Request timeout (accounts for cold start) |
| `EMBEDDING_PROVIDER`| RAG Service | Optional | `fastembed` | Dense embeddings engine |
| `EMBEDDING_MODEL` | RAG Service | Optional | `BAAI/bge-small-en-v1.5` | Embedding model tag (384 dimensions) |
| `VECTOR_STORE_PATH` | RAG Service | Optional | `../data/vectorstore` | ChromaDB persistence path |
| `TOP_K_DEFAULT` | RAG Service | Optional | `5` | Default number of records retrieved |
| `TOP_K_MAX` | RAG Service | Optional | `50` | Maximum top-K cap |
| `SIMILARITY_THRESHOLD` | RAG Service | Optional | `0.58` | Minimum cosine similarity cutoff |

### 4. Local Setup
```bash
# 1. Clone & enter repository
git clone <repo-url> && cd ioi-ai

# 2. Copy and configure environment templates
cp rag-service/.env.example rag-service/.env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# Note: Real credentials and connection strings must be inserted locally into
# backend/.env and rag-service/.env. Never commit real credentials to Git.

# 3. Install dependencies
cd backend && npm install
cd ../frontend && npm install
cd ../rag-service && pip install -r requirements.txt
cd ..

# 4. Pull local LLM model
ollama pull llama3.2:1b
```

### 5. One-Command Startup
```bash
./start.sh
```
The script validates pre-flight dependencies, safely starts any offline services, prints a clean system status banner, runs an automated RAG smoke test, and handles clean shutdown on `Ctrl+C`.

### 6. Production Startup Considerations
- **Process Supervision:** For production servers, manage the services using `systemd`, `pm2`, or container orchestration rather than running development servers in the terminal:
  - Backend: `npm run build && npm start`
  - Frontend: `npm run build && npm start`
  - RAG Service: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`
  - Ollama: `systemctl start ollama`
- **Reverse Proxy:** Terminate SSL/TLS at Nginx or Caddy and route `/api` to port `5001` and UI to port `3000`.

### 7. Cloud Production Deployment (Vercel + Render + Hugging Face Spaces)

For full step-by-step instructions, see the complete guide: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md).

#### Deployment Architecture
| Component | Platform | Configuration File | Key Environment Variables |
|---|---|---|---|
| **Frontend** | [Vercel](https://vercel.com) | `frontend/vercel.json` | `NEXT_PUBLIC_API_URL=https://<your-backend>.onrender.com` |
| **Backend** | [Render](https://render.com) | `render.yaml` | `MONGODB_URI`, `RAG_SERVICE_URL=https://<your-space>.hf.space`, `CORS_ORIGIN` |
| **RAG Service** | [Hugging Face Spaces](https://huggingface.co/spaces) | `rag-service/Dockerfile` | `EMBEDDING_PROVIDER=sentence-transformers`, `LLM_PROVIDER=huggingface`, `HF_TOKEN` |

#### Quick Deployment Sequence
1. **RAG Service (Hugging Face Spaces):** Create a Docker Space (blank), push `rag-service/` contents along with `data/vectorstore_hf/`, and configure `HF_TOKEN`. The container exposes port `7860`.
2. **Backend (Render):** Create a Web Service connected to the GitHub repo using `render.yaml` Blueprint or root directory `backend`. Set `RAG_SERVICE_URL` to the Hugging Face Space URL.
3. **Frontend (Vercel):** Import repository, set Root Directory to `frontend`, and configure `NEXT_PUBLIC_API_URL` to point to the Render backend URL.

### 8. Health Endpoints
- `GET http://localhost:5001/api/health` — Node/Express backend status and MongoDB connectivity
- `GET http://localhost:8000/api/health` — FastAPI status, ChromaDB record count (1,097), and Ollama status
- `GET http://localhost:11434/api/tags` — Ollama model inventory
- `GET http://localhost:3000` — Next.js frontend availability

### 9. API Endpoints
- `POST http://localhost:5001/api/rag/query` — Primary natural language query endpoint
- `GET http://localhost:5001/api/rag/metrics` — Recent telemetry log
- `GET http://localhost:5001/api/rag/metrics/summary` — Aggregated metrics & latency percentiles
- `GET http://localhost:5001/api/students` — Student directory CRUD

### 10. Build Commands
```bash
# Backend TypeScript compilation
cd backend && npm run build

# Frontend Next.js production build
cd frontend && npm run build
```

### 11. Complete Test Suite
```bash
# RAG Unit & Integration Tests
cd rag-service
python3 -m app.scripts.test_metrics
python3 -m app.scripts.test_query_router
python3 -m app.scripts.evaluate_retrieval
python3 -m app.scripts.evaluate_rag
python3 -m app.scripts.test_api
python3 -m app.scripts.evaluate_step_8k
python3 -m app.scripts.benchmark_production_performance

# Backend Tests
cd ../backend
npm run test:rag

# Startup & Smoke Tests
cd ..
bash -n start.sh
./start.sh --check-only
./start.sh --smoke-test
```

### 12. Troubleshooting
- **FastAPI / Express port conflict:** Check listening PIDs: `lsof -nP -i :8000 -sTCP:LISTEN` or `lsof -nP -i :5001 -sTCP:LISTEN`. Re-run `./start.sh` which automatically identifies and reuses compatible processes.
- **Ollama unavailable:** Ensure Ollama is running (`ollama serve`). Verify with `curl http://localhost:11434/api/tags`.
- **Model missing error:** Run `ollama pull llama3.2:1b`.
- **ChromaDB empty:** Rebuild vector store from MongoDB: `cd rag-service && python3 -m app.scripts.build_vector_store`.

### 13. Security Considerations
- **Proxy Isolation:** Browser clients strictly contact Express (`:5001`). No direct browser exposure of FastAPI, MongoDB, or Ollama.
- **Payload Limits:** Express restricts request body size to `1MB` (`express.json({ limit: "1mb" })`).
- **Query Length Caps:** Queries are constrained to `1,000` characters.
- **Sanitized Errors:** Internal server stack traces, database strings, and paths are logged privately and never returned in client HTTP responses.
- **No Committed Secrets:** Database URIs are kept in git-ignored `.env` files.

### 13. Performance Limitations
- **LLM Generation Bottleneck:** Inference on Apple Silicon takes ~2.5–6s per generation. Aggregation queries (counts) bypass the LLM and finish in under 50ms.
- **Cold-Start Penalty:** When first loading `llama3.2:1b` into memory, a one-time ~5–10s cold-start delay may occur. Subsequent warm queries execute in ~3.5s.

### 14. Known Limitations
- **Directory Scope:** Public directory listings only contain basic institutional info (School, Campus, Batch, Gender). Synthetic profiles include sample skills/projects. Private contact info (phone, email, GPA) is intentionally omitted and strictly guarded against hallucination.

---

## Manual Deployment Checklist

Before deploying the IOI AI project to production, review and decide upon each of the following infrastructure and operational requirements. Execute deployment steps manually based on your chosen hosting infrastructure:

### 1. Frontend Hosting
- [ ] Decide on hosting platform for Next.js 16 (e.g., Vercel, Node server, Docker container, or private VM).
- [ ] Ensure the runtime environment supports Next.js App Router and Node.js 18+.
- [ ] Configure `NEXT_PUBLIC_API_URL` to point to the public Express backend proxy URL.

### 2. Express Backend Hosting
- [ ] Select deployment target for Node.js / Express proxy (e.g., containerized VM, serverless container, or dedicated instance).
- [ ] Configure process supervisor (e.g., PM2, systemd, or container restart policy) for production execution (`npm run build && npm start`).
- [ ] Restrict CORS origin in production via `CORS_ORIGIN` environment variable.

### 3. FastAPI RAG Service Hosting
- [ ] Choose host environment for Python 3.10+ FastAPI application.
- [ ] Configure production ASGI server (e.g., `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2` or `gunicorn -k uvicorn.workers.UvicornWorker`).
- [ ] Ensure internal network access between Express backend and FastAPI (`RAG_SERVICE_URL`).

### 4. MongoDB Atlas Configuration
- [ ] Provision MongoDB Atlas database cluster with read-only application user credentials.
- [ ] Configure IP access lists (Network Access) allowing traffic from backend and RAG service hosts.
- [ ] Set `MONGODB_URI` securely in environment configuration without committing credentials to source.

### 5. Ollama Hosting & Model Strategy
- [ ] Determine server host equipped with sufficient CPU/RAM or GPU for Ollama (`llama3.2:1b`).
- [ ] Run `ollama pull llama3.2:1b` on the deployment host.
- [ ] Configure `OLLAMA_BASE_URL` to point to the host instance (e.g., `http://localhost:11434` or internal cluster network).

### 6. ChromaDB Persistent Storage Strategy
- [ ] Provision persistent disk volume for ChromaDB storage (`data/vectorstore/`).
- [ ] Ensure container mounts or file paths retain vector embeddings across container restarts and redeployments.
- [ ] If initial vector store is empty, run `python3 -m app.scripts.build_vector_store` once against MongoDB Atlas.

### 7. Environment Variables
- [ ] Copy and populate `.env` files from templates:
  - `frontend/.env.example` -> `frontend/.env.local` / platform environment variables
  - `backend/.env.example` -> `backend/.env`
  - `rag-service/.env.example` -> `rag-service/.env`
- [ ] Verify no secrets are exposed in client-facing bundles (only `NEXT_PUBLIC_API_URL` is public).

### 8. CORS Configuration
- [ ] Update `CORS_ORIGIN` in both `backend/.env` and `rag-service/.env` from wildcard `*` to the exact production frontend domain.

### 9. Production URLs
- [ ] Assign and verify public DNS / domain names and SSL/TLS certificates.
- [ ] Point `NEXT_PUBLIC_API_URL` to the public Express backend proxy URL (e.g., `https://api.yourdomain.com`).
- [ ] Point `RAG_SERVICE_URL` in Express to the internal/private FastAPI network URL.
- [ ] Confirm browser clients communicate ONLY with the Express backend proxy.

### 10. Health Checks & Monitoring
- [ ] Configure automated uptime checks for:
  - Frontend: `GET https://yourdomain.com`
  - Backend: `GET https://api.yourdomain.com/api/health`
  - RAG Service: `GET http://<rag-internal>:8000/api/health`
- [ ] Monitor telemetry metrics at `GET /api/rag/metrics/summary` to observe latency percentiles (P50, P95) and success rates.


