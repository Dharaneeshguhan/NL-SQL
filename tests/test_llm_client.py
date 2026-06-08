"""Tests for LLM client (mocked — no live API calls)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from agents.llm_client import LLMClient
from utils.errors import LLMConnectionError


class TestLLMClient:
    def test_openrouter_requires_api_key(self):
        client = LLMClient(provider="openrouter", api_key="")
        ok, msg = client.is_available()
        assert ok is False
        assert "API key" in msg

    def test_openrouter_generate_raises_without_key(self):
        client = LLMClient(provider="openrouter", api_key="")
        with pytest.raises(LLMConnectionError):
            client.generate("Hello")

    @patch("agents.llm_client.httpx.Client")
    def test_ollama_connection_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.side_effect = httpx.ConnectError("refused")
        mock_client_cls.return_value = mock_client

        client = LLMClient(provider="ollama", model="llama3")
        with pytest.raises(LLMConnectionError) as exc:
            client.generate("SELECT 1")
        assert "Ollama" in str(exc.value)

    @patch("agents.llm_client.httpx.Client")
    def test_ollama_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "SELECT 1"}
        mock_response.raise_for_status = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = LLMClient(provider="ollama", model="llama3")
        assert client.generate("test") == "SELECT 1"

    @patch("agents.llm_client.httpx.Client")
    def test_ollama_is_available(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "llama3:latest"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.__enter__.return_value.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = LLMClient(provider="ollama", model="llama3")
        ok, msg = client.is_available()
        assert ok is True
