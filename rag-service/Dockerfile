# ==============================================================================
# IOI AI — RAG Service Dockerfile
# Deployment Target: Hugging Face Spaces (Docker Space)
# Exposes Port: 7860
# ==============================================================================

FROM python:3.11-slim

# Prevent writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOST=0.0.0.0 \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    EMBEDDING_PROVIDER=sentence-transformers \
    EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 \
    VECTOR_STORE_PATH=/home/user/app/data/vectorstore_hf \
    LLM_PROVIDER=huggingface \
    HF_MODEL=meta-llama/Llama-3.2-1B-Instruct \
    HF_HOME=/home/user/.cache/huggingface

# Install system dependencies (curl for health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with UID 1000 (standard for Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Set working directory
WORKDIR /home/user/app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model during build to ensure fast, offline-ready startup
RUN mkdir -p /home/user/.cache/huggingface && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" && \
    chown -R user:user /home/user

# Copy application code, deployment vector store, and entrypoint script
COPY --chown=user:user app/ ./app/
COPY --chown=user:user data/vectorstore_hf/ ./data/vectorstore_hf/
COPY --chown=user:user entrypoint.sh ./entrypoint.sh

RUN chmod +x ./entrypoint.sh

# Switch to non-root user
USER user

# Expose default Hugging Face Space port
EXPOSE 7860

# Add container healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
