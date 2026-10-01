"""
RAG Answer Generation Layer for IOI AI.

Combines the retrieval layer (ChromaDB + FastEmbed) with a local LLM runtime (Ollama)
to generate strictly grounded, hallucination-free answers.

Complies with strict RAG constraints:
1. Answers ONLY using provided retrieved context.
2. Does NOT invent missing fields or contact info.
3. Clearly flags missing/insufficient data.
4. Preserves full source traceability.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from typing import Any, Sequence
import urllib.error
import urllib.request

from app.retriever import RetrievalResult, format_context, retrieve_students

# Default local LLM configuration
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:1b"

# Default Hugging Face configuration
DEFAULT_HF_MODEL = "meta-llama/Llama-3.2-1B-Instruct"
DEFAULT_HF_TIMEOUT_SECONDS = 30

SYSTEM_PROMPT = """You are IOI AI, a knowledgeable, strictly factual AI assistant for the PW Institute of Innovation (PW IOI) School of Technology student directory.

STRICT RAG RULES:
1. Answer using ONLY the facts explicitly stated in the retrieved student records.
2. When asked to find or list students matching certain criteria (such as campus, batch, gender, or skills), review the student records provided and list the students whose fields match those criteria.
3. When describing a specific individual student, always state their Name, Campus (e.g., Bengaluru, Pune, Lucknow, Noida), Batch, and School as recorded.
4. The retrieved records represent a sampled top-K match from a directory of 1,097 students. NEVER claim or imply that retrieved results represent the entire school or that "these are the only students in the campus/batch"; state clearly that these are among the retrieved records.
5. NEVER invent or hallucinate student information (such as phone numbers, emails, grades, GPA, or unlisted projects).
6. Do NOT assume or infer missing skills, projects, or interests.
7. If a field states "Not available", it means data is missing; never treat "Not available" as a skill or project.
8. If none of the retrieved records contain the requested information (for example, if asked for phone numbers, GPA, or unrecorded data), clearly state: "The available records do not contain this information."
9. Clearly distinguish public PW IOI records from synthetic/demo records when relevant.
10. Do not expose internal technical IDs unless explicitly asked.
11. Keep your response direct, factual, well-structured, and concise."""


def build_rag_prompt(query: str, context: str) -> str:
    """Format user query and retrieved context into a grounded prompt."""
    return f"""Retrieved Student Records:
-------------------------
{context}
-------------------------

User Question: {query}

Provide a grounded, factual answer based strictly on the student records above:"""


def call_ollama(
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    base_url: str | None = None,
    model: str | None = None,
    timeout_seconds: int | None = None,
) -> str:
    """
    Call local Ollama REST API (/api/chat).

    Args:
        prompt: User prompt containing question and context.
        system_prompt: Instructions constraining model behavior.
        base_url: Ollama HTTP host (defaults to OLLAMA_BASE_URL or http://localhost:11434).
        model: Model tag (defaults to OLLAMA_MODEL or qwen2.5:1.5b).
        timeout_seconds: HTTP request timeout (defaults to OLLAMA_TIMEOUT_SECONDS or 120).

    Returns:
        Generated text response.
    """
    host = (base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    model_name = model or os.environ.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL
    effective_timeout = timeout_seconds or int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120"))

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.0,  # Zero temperature for deterministic, factual outputs
            "num_predict": 300,  # Cap token length to prevent infinite generation loops
        },
    }

    url = f"{host}/api/chat"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content", "").strip()
    except (TimeoutError, socket.timeout) as e:
        raise TimeoutError(
            f"Ollama generation request timed out after {effective_timeout}s at {url}."
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Failed to connect to local Ollama server at {url}. "
            f"Make sure Ollama is installed and running (`ollama serve`). Details: {e}"
        ) from e


def call_huggingface(
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    token: str | None = None,
    model: str | None = None,
    timeout_seconds: int | None = None,
) -> str:
    """
    Call Hugging Face Serverless Inference API (/chat/completions) using official InferenceClient.

    Args:
        prompt: User prompt containing question and context.
        system_prompt: Instructions constraining model behavior.
        token: Hugging Face API token (defaults to HF_TOKEN env var).
        model: Hugging Face model repository tag (defaults to HF_MODEL or meta-llama/Llama-3.2-1B-Instruct).
        timeout_seconds: Request timeout in seconds (defaults to HF_TIMEOUT_SECONDS or 30).

    Returns:
        Generated text response.
    """
    effective_token = token or os.environ.get("HF_TOKEN")
    if not effective_token:
        raise ValueError(
            "HF_TOKEN environment variable is required when LLM_PROVIDER=huggingface. "
            "Please set HF_TOKEN in your environment or .env file."
        )

    model_name = model or os.environ.get("HF_MODEL") or DEFAULT_HF_MODEL
    effective_timeout = timeout_seconds or int(os.environ.get("HF_TIMEOUT_SECONDS", str(DEFAULT_HF_TIMEOUT_SECONDS)))

    try:
        from huggingface_hub import InferenceClient
    except ImportError as e:
        raise RuntimeError(
            "huggingface_hub package is not installed. Please install it with 'pip install huggingface_hub>=0.20.0'."
        ) from e

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    try:
        client = InferenceClient(model=model_name, token=effective_token, timeout=effective_timeout)
        resp = client.chat_completion(
            messages=messages,
            max_tokens=300,
            temperature=0.01,
        )

        # Extract text content safely from response object or dict
        if hasattr(resp, "choices") and resp.choices:
            choice = resp.choices[0]
            if hasattr(choice, "message"):
                msg = choice.message
                if hasattr(msg, "content"):
                    return (msg.content or "").strip()
                elif isinstance(msg, dict):
                    return (msg.get("content") or "").strip()
            elif isinstance(choice, dict):
                return (choice.get("message", {}).get("content") or "").strip()
        elif isinstance(resp, dict):
            choices = resp.get("choices", [])
            if choices:
                return (choices[0].get("message", {}).get("content") or "").strip()

        return str(resp).strip()
    except Exception as e:
        err_msg = str(e)
        if effective_token and effective_token in err_msg:
            err_msg = err_msg.replace(effective_token, "[REDACTED_HF_TOKEN]")
        raise RuntimeError(
            f"Hugging Face inference request failed for model '{model_name}': {err_msg}"
        ) from None


def generate_answer(
    query: str | None = None,
    context: str | None = None,
    prompt: str | None = None,
    provider: str | None = None,
) -> str:
    """
    Generate an answer using the configured LLM provider.

    Supports:
      - 'ollama' (default, local development)
      - 'huggingface' (cloud inference for Hugging Face Spaces deployment)

    Args:
        query: Optional user question (used with context to construct prompt).
        context: Optional retrieved context (used with query to construct prompt).
        prompt: Optional pre-constructed RAG prompt string.
        provider: Provider override ('ollama' or 'huggingface').
    """
    llm_provider = (provider or os.environ.get("LLM_PROVIDER") or "ollama").lower()

    if prompt is None:
        if query is None or context is None:
            raise ValueError("Either 'prompt' or both 'query' and 'context' must be provided.")
        prompt = build_rag_prompt(query, context)

    if llm_provider == "ollama":
        return call_ollama(prompt=prompt)
    elif llm_provider == "huggingface":
        return call_huggingface(prompt=prompt)
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{llm_provider}'. Supported: 'ollama', 'huggingface'"
        )


def generate_rag_response(
    query: str,
    top_k: int = 5,
    campus: str | None = None,
    batch: str | int | None = None,
    gender: str | None = None,
    school: str | None = None,
) -> dict[str, Any]:
    """
    Complete end-to-end RAG pipeline:
    Query -> Retrieve -> Format Context -> Generate LLM Answer -> Return with Source Traceability.

    Returns:
        Dictionary with query, answer, and sources list for full auditability.
    """
    # 1. Retrieve relevant student documents
    retrieved_results: list[RetrievalResult] = retrieve_students(
        query=query,
        top_k=top_k,
        campus=campus,
        batch=batch,
        gender=gender,
        school=school,
    )

    # 2. Format grounded context
    context = format_context(retrieved_results)

    # 3. Call local LLM
    answer = generate_answer(query=query, context=context)

    # 4. Assemble traceable sources
    sources = [
        {
            "student_id": r.document_id,
            "document_id": r.document_id,
            "name": r.name,
            "campus": r.campus,
            "batch": r.batch,
            "gender": r.gender,
            "similarity_score": r.similarity_score,
            "source_type": r.source_type,
            "source_status": r.source_status,
        }
        for r in retrieved_results
    ]

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
    }
