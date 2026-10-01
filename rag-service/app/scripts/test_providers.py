"""
Provider & Generation Layer Test Suite for IOI AI.

Tests:
1. Ollama provider selection
2. Hugging Face provider selection (mocked InferenceClient)
3. Invalid provider configuration handling
4. Missing HF_TOKEN handling
5. Provider failure handling (error sanitization, token redaction, no stack leaks)
6. Existing RAG behavior (query, answer, sources returned)
7. Privacy refusal (unsupported fields rejected safely without LLM call)
8. Deterministic student-profile formatting

Usage:
    cd rag-service
    python -m app.scripts.test_providers
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.embeddings import (
    embed_documents,
    embed_text,
    get_embedding_model,
    reset_embedding_model,
)
from app.generator import (
    DEFAULT_HF_MODEL,
    DEFAULT_OLLAMA_MODEL,
    call_huggingface,
    call_ollama,
    generate_answer,
    generate_rag_response,
)
from app.query_router import route_and_execute_query


class TestProviderGeneration(unittest.TestCase):
    """Unit and integration tests for multi-provider LLM generation layer."""

    def setUp(self) -> None:
        self.original_env = os.environ.copy()
        reset_embedding_model()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.original_env)
        reset_embedding_model()

    @patch("app.generator.call_ollama")
    def test_01_ollama_provider_selection(self, mock_call_ollama: MagicMock) -> None:
        """Verify LLM_PROVIDER=ollama routes generation to call_ollama."""
        os.environ["LLM_PROVIDER"] = "ollama"
        mock_call_ollama.return_value = "Ollama generated response"

        answer = generate_answer(query="Test query", context="Sample context")
        self.assertEqual(answer, "Ollama generated response")
        self.assertTrue(mock_call_ollama.called)

    @patch("huggingface_hub.InferenceClient")
    def test_02_huggingface_provider_selection(self, mock_client_cls: MagicMock) -> None:
        """Verify LLM_PROVIDER=huggingface routes generation to Hugging Face with expected params."""
        os.environ["LLM_PROVIDER"] = "huggingface"
        os.environ["HF_TOKEN"] = "hf_mock_token_secret_123"
        os.environ["HF_MODEL"] = "meta-llama/Llama-3.2-1B-Instruct"

        mock_choice = MagicMock()
        mock_choice.message.content = "Hugging Face grounded response"
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        mock_client_instance = MagicMock()
        mock_client_instance.chat_completion.return_value = mock_resp
        mock_client_cls.return_value = mock_client_instance

        answer = generate_answer(query="Who is Sagar?", context="Sagar is in Bengaluru")
        self.assertEqual(answer, "Hugging Face grounded response")

        # Verify InferenceClient was initialized with the configured token and model
        mock_client_cls.assert_called_once_with(
            model="meta-llama/Llama-3.2-1B-Instruct",
            token="hf_mock_token_secret_123",
            timeout=30,
        )
        self.assertTrue(mock_client_instance.chat_completion.called)
        call_kwargs = mock_client_instance.chat_completion.call_args[1]
        self.assertEqual(call_kwargs.get("max_tokens"), 300)
        self.assertEqual(call_kwargs.get("temperature"), 0.01)

    def test_03_invalid_provider_configuration(self) -> None:
        """Verify invalid LLM_PROVIDER raises a clean ValueError."""
        os.environ["LLM_PROVIDER"] = "unsupported_cloud_provider"

        with self.assertRaises(ValueError) as ctx:
            generate_answer(query="Test", context="Context")

        self.assertIn("Unsupported LLM_PROVIDER", str(ctx.exception))
        self.assertIn("ollama", str(ctx.exception))
        self.assertIn("huggingface", str(ctx.exception))

    def test_04_missing_hf_token(self) -> None:
        """Verify missing HF_TOKEN raises a clean, informative ValueError."""
        os.environ["LLM_PROVIDER"] = "huggingface"
        if "HF_TOKEN" in os.environ:
            del os.environ["HF_TOKEN"]

        with self.assertRaises(ValueError) as ctx:
            generate_answer(query="Test", context="Context")

        self.assertIn("HF_TOKEN environment variable is required", str(ctx.exception))

    @patch("huggingface_hub.InferenceClient")
    def test_05_provider_failure_handling(self, mock_client_cls: MagicMock) -> None:
        """Verify Hugging Face API errors are sanitized without exposing the secret token."""
        test_secret_token = "hf_SUPER_SECRET_TOKEN_999"
        os.environ["LLM_PROVIDER"] = "huggingface"
        os.environ["HF_TOKEN"] = test_secret_token

        mock_client_instance = MagicMock()
        mock_client_instance.chat_completion.side_effect = Exception(
            f"HTTP 401 Unauthorized for token {test_secret_token} on server"
        )
        mock_client_cls.return_value = mock_client_instance

        with self.assertRaises(RuntimeError) as ctx:
            generate_answer(query="Test", context="Context")

        err_msg = str(ctx.exception)
        # Token must NOT appear anywhere in the error message
        self.assertNotIn(test_secret_token, err_msg)
        self.assertIn("[REDACTED_HF_TOKEN]", err_msg)
        self.assertIn("Hugging Face inference request failed", err_msg)

    @patch("app.generator.call_ollama")
    def test_06_existing_rag_behavior(self, mock_call_ollama: MagicMock) -> None:
        """Verify generate_rag_response returns query, answer, and grounded sources."""
        os.environ["LLM_PROVIDER"] = "ollama"
        mock_call_ollama.return_value = "Based on records, Sagar Gupta is a student."

        res = generate_rag_response(query="Who are some students from Bengaluru?", top_k=2)
        self.assertIn("query", res)
        self.assertIn("answer", res)
        self.assertIn("sources", res)
        self.assertGreaterEqual(len(res["sources"]), 1)
        self.assertIn("student_id", res["sources"][0])
        self.assertIn("similarity_score", res["sources"][0])

    def test_07_privacy_refusal(self) -> None:
        """Verify privacy guardrails refuse sensitive queries deterministically without LLM."""
        res = route_and_execute_query("What is Aarushi Mandloi's phone number?")
        self.assertEqual(res["query_type"], "unsupported")
        self.assertIn("private and not available", res["answer"].lower())

    def test_08_deterministic_student_profile_formatting(self) -> None:
        """Verify deterministic student profile format is preserved across queries."""
        res = route_and_execute_query("Esha Bajaj")
        self.assertEqual(res["query_type"], "semantic")
        self.assertIn("Student Name: Esha Bajaj", res["answer"])
        self.assertIn("School:", res["answer"])
        self.assertIn("Campus:", res["answer"])
        self.assertIn("Batch:", res["answer"])


class TestEmbeddingProviders(unittest.TestCase):
    """Unit tests for multi-provider embedding layer (sentence-transformers, fastembed, error handling)."""

    def setUp(self) -> None:
        self.original_env = os.environ.copy()
        reset_embedding_model()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.original_env)
        reset_embedding_model()

    def test_01_sentence_transformers_embedding(self) -> None:
        """Verify EMBEDDING_PROVIDER=sentence-transformers loads all-MiniLM-L6-v2 and yields 384d float vectors."""
        os.environ["EMBEDDING_PROVIDER"] = "sentence-transformers"
        model_info = get_embedding_model()
        self.assertIsInstance(model_info, tuple)
        self.assertEqual(model_info[0], "sentence-transformers")
        self.assertEqual(model_info[2], "sentence-transformers/all-MiniLM-L6-v2")

        emb = embed_text("IOI AI test sentence for sentence-transformers")
        self.assertIsInstance(emb, list)
        self.assertEqual(len(emb), 384)
        self.assertTrue(all(isinstance(x, float) for x in emb))

        batch = embed_documents(["Text 1", "Text 2"], batch_size=2)
        self.assertEqual(len(batch), 2)
        self.assertEqual(len(batch[0]), 384)
        self.assertEqual(len(batch[1]), 384)

    def test_02_fastembed_embedding(self) -> None:
        """Verify EMBEDDING_PROVIDER=fastembed loads BAAI/bge-small-en-v1.5 and yields 384d float vectors."""
        os.environ["EMBEDDING_PROVIDER"] = "fastembed"
        emb = embed_text("FastEmbed local test")
        self.assertIsInstance(emb, list)
        self.assertEqual(len(emb), 384)
        self.assertTrue(all(isinstance(x, float) for x in emb))

    def test_03_invalid_embedding_provider(self) -> None:
        """Verify unsupported EMBEDDING_PROVIDER raises a clean ValueError."""
        os.environ["EMBEDDING_PROVIDER"] = "unsupported_embed_provider"
        with self.assertRaises(ValueError) as ctx:
            get_embedding_model()
        self.assertIn("Unsupported EMBEDDING_PROVIDER", str(ctx.exception))
        self.assertIn("sentence-transformers", str(ctx.exception))
        self.assertIn("fastembed", str(ctx.exception))


def main() -> None:
    print("=" * 60)
    print("IOI AI — LLM & EMBEDDING PROVIDER TEST SUITE")
    print("=" * 60)
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
