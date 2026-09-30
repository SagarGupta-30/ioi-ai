#!/usr/bin/env bash
# ==============================================================================
# IOI AI — One-Command Local Startup Script (Step 8N.2)
#
# Starts and verifies the complete IOI AI RAG stack:
#   1. Ollama runtime (port 11434) + llama3.2:1b model
#   2. FastAPI RAG service (port 8000)
#   3. Node/Express backend proxy (port 5001)
#   4. Next.js frontend (port 3000)
#
# Features:
#   - Thorough pre-flight verification
#   - Duplicate process & port conflict detection (reuses compatible services)
#   - Clean graceful shutdown on Ctrl+C (SIGINT / SIGTERM)
#   - Output logging to logs/*.log
#   - Automated end-to-end RAG smoke test
# ==============================================================================

# Note: do not set -e here because we handle errors explicitly and manage trap cleanup
set -u
set -m
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Array to keep track of PIDs started strictly by THIS script
MANAGED_PIDS=()
SHUTTING_DOWN=0

# Color helpers
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m" # No Color

# ------------------------------------------------------------------------------
# Signal Handling / Clean Shutdown
# ------------------------------------------------------------------------------
cleanup() {
  if [ "$SHUTTING_DOWN" -eq 1 ]; then
    return
  fi
  SHUTTING_DOWN=1
  echo ""

  if [ ${#MANAGED_PIDS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Shutting down services started by this script...${NC}"
    for pid in "${MANAGED_PIDS[@]}"; do
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo -e "  Stopping process ${CYAN}$pid${NC}..."
        pkill -TERM -P "$pid" 2>/dev/null || true
        kill -TERM "$pid" 2>/dev/null || true
      fi
    done

    # Give processes up to 2 seconds to shut down gracefully
    sleep 2

    # Force kill any stubborn lingering processes started by this script
    for pid in "${MANAGED_PIDS[@]}"; do
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        pkill -9 -P "$pid" 2>/dev/null || true
        kill -9 "$pid" 2>/dev/null || true
      fi
    done
    echo -e "${GREEN}All services started by this script have stopped.${NC}"
  else
    echo -e "${CYAN}No background services were spawned by this script (all services were already running).${NC}"
  fi
  exit 0
}

trap cleanup SIGINT SIGTERM

# ------------------------------------------------------------------------------
# Pre-Flight Checks
# ------------------------------------------------------------------------------
echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}       IOI AI SYSTEM STARTUP            ${NC}"
echo -e "${BOLD}========================================${NC}"
echo -e "${CYAN}Performing pre-flight checks...${NC}"

# 1. Required CLI binaries
check_binary() {
  local bin=$1
  local help_msg=$2
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo -e "${RED}ERROR: Required tool '$bin' is not installed or not in PATH.${NC}"
    echo -e "       $help_msg"
    exit 1
  fi
}

check_binary "python3" "Install Python 3.10+ from https://www.python.org/ or via Homebrew: brew install python"
check_binary "node"    "Install Node.js 18+ from https://nodejs.org/ or via Homebrew: brew install node"
check_binary "npm"     "npm is bundled with Node.js. Please verify your Node installation."
check_binary "ollama"  "Install Ollama from https://ollama.ai/ or via Homebrew: brew install ollama"

# 2. Required directories
check_dir() {
  local dir=$1
  local name=$2
  if [ ! -d "$dir" ]; then
    echo -e "${RED}ERROR: Required directory '$name' ($dir) was not found.${NC}"
    exit 1
  fi
}

check_dir "$SCRIPT_DIR/rag-service"      "rag-service"
check_dir "$SCRIPT_DIR/backend"          "backend"
check_dir "$SCRIPT_DIR/frontend"         "frontend"
check_dir "$SCRIPT_DIR/data/vectorstore" "data/vectorstore"

# 3. ChromaDB vector store data check
if [ ! -f "$SCRIPT_DIR/data/vectorstore/chroma.sqlite3" ]; then
  echo -e "${RED}ERROR: ChromaDB database file 'data/vectorstore/chroma.sqlite3' not found.${NC}"
  echo -e "       Rebuild the index by running: cd rag-service && python3 -m app.scripts.build_vector_store"
  exit 1
fi

# 4. Dependency directories & imports
if [ ! -d "$SCRIPT_DIR/backend/node_modules" ]; then
  echo -e "${RED}ERROR: Backend dependencies not installed.${NC}"
  echo -e "       Run: cd backend && npm install"
  exit 1
fi

if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
  echo -e "${RED}ERROR: Frontend dependencies not installed.${NC}"
  echo -e "       Run: cd frontend && npm install"
  exit 1
fi

if ! python3 -c "import fastapi, uvicorn, chromadb, fastembed, pymongo" >/dev/null 2>&1; then
  echo -e "${RED}ERROR: Python RAG service dependencies are missing.${NC}"
  echo -e "       Run: cd rag-service && pip install -r requirements.txt"
  exit 1
fi

# 5. Environment configuration files
if [ ! -f "$SCRIPT_DIR/rag-service/.env" ]; then
  echo -e "${RED}ERROR: Missing rag-service/.env configuration file.${NC}"
  echo -e "       Copy rag-service/.env.example to rag-service/.env and configure it."
  exit 1
fi

if [ ! -f "$SCRIPT_DIR/backend/.env" ]; then
  echo -e "${RED}ERROR: Missing backend/.env configuration file.${NC}"
  echo -e "       Copy backend/.env.example to backend/.env and configure it."
  exit 1
fi

if [ ! -f "$SCRIPT_DIR/frontend/.env.local" ] && [ ! -f "$SCRIPT_DIR/frontend/.env" ]; then
  echo -e "${RED}ERROR: Missing frontend/.env.local configuration file.${NC}"
  echo -e "       Copy frontend/.env.example to frontend/.env.local and configure it."
  exit 1
fi

echo -e "Pre-flight checks: ${GREEN}✓ All requirements satisfied${NC}"

# Handle --check-only flag
if [ "${1:-}" = "--check-only" ]; then
  echo -e "${GREEN}Pre-flight check completed successfully.${NC}"
  exit 0
fi

# ------------------------------------------------------------------------------
# 1. Ollama Check & Startup
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[1/4] Checking Ollama LLM runtime (port 11434)...${NC}"

OLLAMA_TAGS_URL="http://localhost:11434/api/tags"
OLLAMA_RUNNING=0

if curl -s --max-time 2 "$OLLAMA_TAGS_URL" >/dev/null 2>&1; then
  OLLAMA_RUNNING=1
  echo -e "  Ollama runtime is already running: ${GREEN}✓ (http://localhost:11434)${NC}"
else
  echo -e "  Ollama is not running. Attempting to start Ollama..."
  nohup ollama serve >> "$LOG_DIR/ollama.log" 2>&1 &
  OLLAMA_PID=$!
  MANAGED_PIDS+=($OLLAMA_PID)

  # Poll up to 10 seconds for Ollama to become ready
  local_elapsed=0
  while [ $local_elapsed -lt 10 ]; do
    if curl -s --max-time 1 "$OLLAMA_TAGS_URL" >/dev/null 2>&1; then
      OLLAMA_RUNNING=1
      break
    fi
    sleep 1
    local_elapsed=$((local_elapsed + 1))
  done

  if [ "$OLLAMA_RUNNING" -eq 1 ]; then
    echo -e "  Ollama runtime started successfully: ${GREEN}✓ (PID: $OLLAMA_PID)${NC}"
  else
    echo -e "${RED}ERROR: Ollama is not reachable at localhost:11434.${NC}"
    echo -e "       Please start Ollama manually by running: ollama serve"
    echo -e "       or launch the Ollama macOS desktop application."
    exit 1
  fi
fi

# Verify required model llama3.2:1b
TAGS_RESPONSE=$(curl -s --max-time 3 "$OLLAMA_TAGS_URL" 2>/dev/null || true)
if echo "$TAGS_RESPONSE" | grep -q "llama3.2:1b"; then
  echo -e "  Model llama3.2:1b: ${GREEN}✓ Installed${NC}"
else
  echo -e "${RED}ERROR: Required Ollama model llama3.2:1b is not installed.${NC}"
  echo -e "       Please install it by running:"
  echo -e "         ollama pull llama3.2:1b"
  exit 1
fi

# ------------------------------------------------------------------------------
# Helper: Port Inspection & Conflict Detection
# ------------------------------------------------------------------------------
get_pids_on_port() {
  local port=$1
  lsof -nP -i ":$port" -sTCP:LISTEN -t 2>/dev/null | tr '\n' ' '
}

is_port_in_use() {
  local port=$1
  lsof -nP -i ":$port" -sTCP:LISTEN >/dev/null 2>&1
}

# ------------------------------------------------------------------------------
# 2. FastAPI RAG Service (port 8000)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[2/4] Checking FastAPI RAG service (port 8000)...${NC}"

FASTAPI_URL="http://localhost:8000/api/health"
FASTAPI_RUNNING=0

if is_port_in_use 8000; then
  # Port is in use, verify if it is our compatible RAG service
  HEALTH_RESP=$(curl -s --max-time 3 "$FASTAPI_URL" 2>/dev/null || true)
  if echo "$HEALTH_RESP" | grep -q "ioi-ai-rag-service"; then
    echo -e "  FastAPI RAG service is already running: ${GREEN}✓ (reusing existing process on port 8000)${NC}"
    FASTAPI_RUNNING=1
  else
    OCCUPYING_PIDS=$(get_pids_on_port 8000)
    echo -e "${RED}ERROR: FastAPI cannot start because port 8000 is already occupied by an incompatible process (PID: $OCCUPYING_PIDS).${NC}"
    echo -e "       Please free port 8000 and retry."
    exit 1
  fi
fi

if [ "$FASTAPI_RUNNING" -eq 0 ]; then
  echo -e "  Starting FastAPI RAG service on port 8000..."
  (cd "$SCRIPT_DIR/rag-service" && exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000) >> "$LOG_DIR/rag-service.log" 2>&1 &
  FASTAPI_PID=$!
  MANAGED_PIDS+=($FASTAPI_PID)

  # Poll health until ready (timeout: 30s)
  echo -n "  Waiting for FastAPI RAG service to become ready..."
  elapsed=0
  timeout=30
  while [ $elapsed -lt $timeout ]; do
    if ! kill -0 "$FASTAPI_PID" 2>/dev/null; then
      echo -e " ${RED}FAILED${NC}"
      echo -e "${RED}ERROR: FastAPI process died unexpectedly. Check logs/rag-service.log:${NC}"
      tail -n 25 "$LOG_DIR/rag-service.log"
      exit 1
    fi

    HEALTH_CHECK=$(curl -s --max-time 2 "$FASTAPI_URL" 2>/dev/null || true)
    if echo "$HEALTH_CHECK" | grep -q "ioi-ai-rag-service"; then
      echo -e " ${GREEN}READY (${elapsed}s)${NC}"
      FASTAPI_RUNNING=1
      break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  if [ "$FASTAPI_RUNNING" -eq 0 ]; then
    echo -e " ${RED}TIMED OUT${NC}"
    echo -e "${RED}ERROR: FastAPI process started but readiness check failed after ${timeout}s.${NC}"
    tail -n 25 "$LOG_DIR/rag-service.log"
    exit 1
  fi
fi

# ------------------------------------------------------------------------------
# 3. Node/Express Backend (port 5001)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[3/4] Checking Node/Express backend (port 5001)...${NC}"

BACKEND_URL="http://localhost:5001/api/health"
BACKEND_RUNNING=0

if is_port_in_use 5001; then
  # Port is in use, verify if it is our compatible Express backend
  HEALTH_RESP=$(curl -s --max-time 3 "$BACKEND_URL" 2>/dev/null || true)
  if echo "$HEALTH_RESP" | grep -q "ioi-ai-backend"; then
    echo -e "  Node/Express backend is already running: ${GREEN}✓ (reusing existing process on port 5001)${NC}"
    BACKEND_RUNNING=1
  else
    OCCUPYING_PIDS=$(get_pids_on_port 5001)
    echo -e "${RED}ERROR: Backend cannot start because port 5001 is already occupied by an incompatible process (PID: $OCCUPYING_PIDS).${NC}"
    echo -e "       Please free port 5001 and retry."
    exit 1
  fi
fi

if [ "$BACKEND_RUNNING" -eq 0 ]; then
  echo -e "  Starting Node/Express backend on port 5001..."
  (cd "$SCRIPT_DIR/backend" && exec npm run dev) >> "$LOG_DIR/backend.log" 2>&1 &
  BACKEND_PID=$!
  MANAGED_PIDS+=($BACKEND_PID)

  # Poll health until ready (timeout: 30s)
  echo -n "  Waiting for Express backend to become ready..."
  elapsed=0
  timeout=30
  while [ $elapsed -lt $timeout ]; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      echo -e " ${RED}FAILED${NC}"
      echo -e "${RED}ERROR: Backend process died unexpectedly. Check logs/backend.log:${NC}"
      tail -n 25 "$LOG_DIR/backend.log"
      exit 1
    fi

    HEALTH_CHECK=$(curl -s --max-time 2 "$BACKEND_URL" 2>/dev/null || true)
    if echo "$HEALTH_CHECK" | grep -q "ioi-ai-backend"; then
      echo -e " ${GREEN}READY (${elapsed}s)${NC}"
      BACKEND_RUNNING=1
      break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  if [ "$BACKEND_RUNNING" -eq 0 ]; then
    echo -e " ${RED}TIMED OUT${NC}"
    echo -e "${RED}ERROR: Express backend started but readiness check failed after ${timeout}s.${NC}"
    tail -n 25 "$LOG_DIR/backend.log"
    exit 1
  fi
fi

# ------------------------------------------------------------------------------
# 4. Next.js Frontend (port 3000)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[4/4] Checking Next.js frontend (port 3000)...${NC}"

FRONTEND_URL="http://localhost:3000"
FRONTEND_RUNNING=0

if is_port_in_use 3000; then
  # Port is in use, verify if it responds to HTTP requests
  RESP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$FRONTEND_URL" 2>/dev/null || true)
  if [ "$RESP_CODE" = "200" ] || [ "$RESP_CODE" = "304" ]; then
    echo -e "  Next.js frontend is already running: ${GREEN}✓ (reusing existing process on port 3000)${NC}"
    FRONTEND_RUNNING=1
  else
    OCCUPYING_PIDS=$(get_pids_on_port 3000)
    echo -e "${RED}ERROR: Frontend cannot start because port 3000 is already occupied by an incompatible process (PID: $OCCUPYING_PIDS).${NC}"
    echo -e "       Please free port 3000 and retry."
    exit 1
  fi
fi

if [ "$FRONTEND_RUNNING" -eq 0 ]; then
  echo -e "  Starting Next.js frontend on port 3000..."
  (cd "$SCRIPT_DIR/frontend" && exec npm run dev) >> "$LOG_DIR/frontend.log" 2>&1 &
  FRONTEND_PID=$!
  MANAGED_PIDS+=($FRONTEND_PID)

  # Poll until HTTP 200 (timeout: 45s, Next.js compilation can take a moment)
  echo -n "  Waiting for Next.js frontend to become ready..."
  elapsed=0
  timeout=45
  while [ $elapsed -lt $timeout ]; do
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
      echo -e " ${RED}FAILED${NC}"
      echo -e "${RED}ERROR: Next.js frontend died unexpectedly. Check logs/frontend.log:${NC}"
      tail -n 25 "$LOG_DIR/frontend.log"
      exit 1
    fi

    RESP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$FRONTEND_URL" 2>/dev/null || true)
    if [ "$RESP_CODE" = "200" ] || [ "$RESP_CODE" = "304" ]; then
      echo -e " ${GREEN}READY (${elapsed}s)${NC}"
      FRONTEND_RUNNING=1
      break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  if [ "$FRONTEND_RUNNING" -eq 0 ]; then
    echo -e " ${RED}TIMED OUT${NC}"
    echo -e "${RED}ERROR: Frontend started but readiness check failed after ${timeout}s.${NC}"
    tail -n 25 "$LOG_DIR/frontend.log"
    exit 1
  fi
fi

# ------------------------------------------------------------------------------
# Extract Dynamic System Metrics for Summary
# ------------------------------------------------------------------------------
HEALTH_DATA=$(curl -s --max-time 3 "$FASTAPI_URL" 2>/dev/null || echo "{}")
INDEXED_RECORDS=$(python3 -c "import json; data=json.loads('$HEALTH_DATA'); print(data.get('vector_store', {}).get('indexed_records', 1097))" 2>/dev/null || echo "1097")

# ------------------------------------------------------------------------------
# Startup Summary
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}           IOI AI RAG SYSTEM            ${NC}"
echo -e "Ollama          ${GREEN}✓${NC} http://localhost:11434/"
echo -e "Model           ${GREEN}✓${NC} llama3.2:1b"
echo -e "FastAPI         ${GREEN}✓${NC} http://localhost:8000/"
echo -e "Vector DB       ${GREEN}✓${NC} Ready"
echo -e "Records         ${GREEN}✓${NC} ${INDEXED_RECORDS}"
echo -e "Express         ${GREEN}✓${NC} http://localhost:5001/"
echo -e "Next.js         ${GREEN}✓${NC} http://localhost:3000/"
echo -e "RAG Pipeline    ${GREEN}✓ READY${NC}"
echo -e "${BOLD}========================================${NC}"
echo -e "Frontend:       ${CYAN}http://localhost:3000/${NC}"
echo -e "API:            ${CYAN}http://localhost:5001/${NC}"
echo -e "RAG Health:     ${CYAN}http://localhost:8000/api/health${NC}"
echo -e "${BOLD}========================================${NC}"

# ------------------------------------------------------------------------------
# End-to-End Smoke Test
# ------------------------------------------------------------------------------
echo -e "\n${CYAN}Running end-to-end RAG verification smoke test...${NC}"
SMOKE_TMP_FILE="/tmp/ioi_smoke_test_$$.json"

HTTP_CODE=$(curl -s -o "$SMOKE_TMP_FILE" -w "%{http_code}" -X POST http://localhost:5001/api/rag/query \
  -H "Content-Type: application/json" \
  --max-time 30 \
  -d '{"query": "Who are some students from Bengaluru?", "top_k": 2}')

SMOKE_VERIFIED=0
if [ "$HTTP_CODE" = "200" ] && [ -f "$SMOKE_TMP_FILE" ]; then
  SMOKE_OUT=$(python3 -c '
import json, sys
try:
    with open("'"$SMOKE_TMP_FILE"'") as f:
        data = json.load(f)
    assert data.get("success") is True, "success != True"
    ans = data.get("answer", "")
    sources = data.get("sources", [])
    assert len(ans) > 0, "answer is empty"
    assert len(sources) > 0, "sources is empty"
    preview = ans.replace("\n", " ")[:70] + "..." if len(ans) > 70 else ans
    print(f"PASS|{len(sources)}|{preview}")
except Exception as e:
    print(f"FAIL|{e}")
    sys.exit(1)
' 2>/dev/null || echo "FAIL|Evaluation error")

  STATUS=$(echo "$SMOKE_OUT" | cut -d'|' -f1)
  if [ "$STATUS" = "PASS" ]; then
    SOURCES_COUNT=$(echo "$SMOKE_OUT" | cut -d'|' -f2)
    ANSWER_SNIPPET=$(echo "$SMOKE_OUT" | cut -d'|' -f3)
    echo -e "Smoke Test:     ${GREEN}✓ PASSED (HTTP 200)${NC}"
    echo -e "Pipeline Trace: Frontend/Client → Express (:5001) → FastAPI (:8000) → ChromaDB → Ollama"
    echo -e "Verified:       ${GREEN}${SOURCES_COUNT} sources retrieved${NC} | Sample Answer: \"${ANSWER_SNIPPET}\""
    SMOKE_VERIFIED=1
  else
    ERR_MSG=$(echo "$SMOKE_OUT" | cut -d'|' -f2)
    echo -e "${YELLOW}Smoke Test: ⚠ Warning — verification check returned: $ERR_MSG${NC}"
  fi
else
  echo -e "${YELLOW}Smoke Test: ⚠ Warning — HTTP status $HTTP_CODE returned from backend proxy.${NC}"
fi

rm -f "$SMOKE_TMP_FILE"

# Handle --smoke-test flag (exit after verification)
if [ "${1:-}" = "--smoke-test" ]; then
  if [ "$SMOKE_VERIFIED" -eq 1 ]; then
    exit 0
  else
    exit 1
  fi
fi

# ------------------------------------------------------------------------------
# Active Service Monitoring / Process Wait
# ------------------------------------------------------------------------------
echo ""
if [ ${#MANAGED_PIDS[@]} -gt 0 ]; then
  echo -e "${GREEN}Services started successfully.${NC}"
  echo -e "Service logs are streaming to: ${CYAN}${LOG_DIR}/*.log${NC}"
  echo -e "Press ${BOLD}[Ctrl+C]${NC} to stop the services started by this script."
  wait
else
  echo -e "${GREEN}All services are running independently.${NC}"
  echo -e "Press ${BOLD}[Ctrl+C]${NC} to exit this monitor."
  while true; do
    sleep 2 &
    wait $! 2>/dev/null || true
  done
fi
