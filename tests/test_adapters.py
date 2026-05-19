"""Tests for LLM adapter layer."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cliniq.adapters import get_adapter
from cliniq.adapters.ollama import OllamaAdapter, _extract_json


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


def test_ollama_complete_json_sends_format_param() -> None:
    with patch("cliniq.adapters.ollama.httpx.post") as mock_post:
        mock_post.return_value = _mock_response('{"ok": true}')
        OllamaAdapter().complete_json(system="sys", user="extract", schema={})

    payload = mock_post.call_args[1]["json"]
    assert payload.get("format") == "json"


def test_ollama_complete_json_markdown_fence() -> None:
    data = {"x": 1}
    fenced = f"```json\n{json.dumps(data)}\n```"
    with patch("cliniq.adapters.ollama.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(fenced)
        result = OllamaAdapter().complete_json(system="sys", user="u", schema={})
    assert result == data


def test_ollama_complete_json_array_response() -> None:
    data = [{"name": "Drug A"}, {"name": "Drug B"}]
    with patch("cliniq.adapters.ollama.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(json.dumps(data))
        result = OllamaAdapter().complete_json(system="sys", user="u", schema={})
    assert result == data


def test_ollama_complete_json_no_json_raises() -> None:
    with patch("cliniq.adapters.ollama.httpx.post") as mock_post:
        mock_post.return_value = _mock_response("sorry I cannot help with that")
        with pytest.raises(ValueError, match="no JSON structure"):
            OllamaAdapter().complete_json(system="sys", user="u", schema={})


def test_ollama_custom_base_url() -> None:
    adapter = OllamaAdapter(base_url="http://custom:9999")
    assert adapter.base_url == "http://custom:9999"


# ---------------------------------------------------------------------------
# _extract_json unit tests
# ---------------------------------------------------------------------------


def test_extract_json_plain_object() -> None:
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_preamble() -> None:
    assert _extract_json('Sure! Here you go: {"a": 1}') == {"a": 1}


def test_extract_json_array() -> None:
    assert _extract_json("[1, 2, 3]") == [1, 2, 3]


def test_extract_json_markdown_fence_json_tag() -> None:
    assert _extract_json('```json\n{"k": "v"}\n```') == {"k": "v"}


def test_extract_json_markdown_fence_no_tag() -> None:
    assert _extract_json('```\n{"k": "v"}\n```') == {"k": "v"}


def test_extract_json_no_structure_raises() -> None:
    with pytest.raises(ValueError, match="no JSON structure"):
        _extract_json("this is plain text with no JSON")


def test_extract_json_array_before_object() -> None:
    result = _extract_json('[{"a": 1}]')
    assert result == [{"a": 1}]
