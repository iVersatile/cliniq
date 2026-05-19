"""Tests for LLM adapter layer."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cliniq.adapters import get_adapter
from cliniq.adapters.ollama import OllamaAdapter


def _mock_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"message": {"content": content}}
    resp.raise_for_status.return_value = None
    return resp


def test_get_adapter_ollama() -> None:
    adapter = get_adapter("ollama")
    assert isinstance(adapter, OllamaAdapter)


def test_get_adapter_unknown() -> None:
    with pytest.raises(NotImplementedError):
        get_adapter("unknown_backend")


def test_ollama_complete() -> None:
    with patch("cliniq.adapters.ollama.httpx.post") as mock_post:
        mock_post.return_value = _mock_response("hello world")
        adapter = OllamaAdapter()
        result = adapter.complete(system="sys", user="hello")
    assert result == "hello world"


def test_ollama_complete_sends_correct_payload() -> None:
    with patch("cliniq.adapters.ollama.httpx.post") as mock_post:
        mock_post.return_value = _mock_response("ok")
        adapter = OllamaAdapter(model="phi3:mini", base_url="http://localhost:11434")
        adapter.complete(system="sys", user="msg")

    call_kwargs = mock_post.call_args
    payload = call_kwargs[1]["json"]
    assert payload["model"] == "phi3:mini"
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"


def test_ollama_complete_json() -> None:
    data = {"name": "Amlodipine", "dose": "5mg"}
    with patch("cliniq.adapters.ollama.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(f"Here is your JSON: {json.dumps(data)}")
        adapter = OllamaAdapter()
        result = adapter.complete_json(system="sys", user="extract", schema={})
    assert result["name"] == "Amlodipine"


def test_ollama_custom_base_url() -> None:
    adapter = OllamaAdapter(base_url="http://custom:9999")
    assert adapter.base_url == "http://custom:9999"
