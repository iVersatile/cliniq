"""Ollama adapter — default local backend (CPU-only)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from cliniq.adapters.base import LLMAdapter

_DEFAULT_MODEL = "phi3:mini"
_DEFAULT_BASE_URL = "http://localhost:11434"

log = logging.getLogger(__name__)


def _extract_json(raw: str) -> Any:
    """Strip optional markdown fences and return the outermost JSON value."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        stripped = "\n".join(inner).strip()

    obj_start = stripped.find("{")
    arr_start = stripped.find("[")

    if obj_start == -1 and arr_start == -1:
        raise ValueError("no JSON structure found in response")

    if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
        start = arr_start
        end = stripped.rfind("]") + 1
    else:
        start = obj_start
        end = stripped.rfind("}") + 1

    substring = stripped[start:end]
    try:
        return json.loads(substring)
    except json.JSONDecodeError as exc:
        log.error("_extract_json: malformed JSON substring: %r", substring[:200])
        raise ValueError(f"malformed JSON in LLM response: {exc}") from exc


class OllamaAdapter(LLMAdapter):
    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", _DEFAULT_BASE_URL)
        self._client = httpx.Client(timeout=120.0)

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001
            pass

    def complete(self, system: str, user: str) -> str:
        response = self._client.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
            },
        )
        response.raise_for_status()
        return str(response.json()["message"]["content"])

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> Any:
        schema_str = json.dumps(schema, indent=2)
        prompt = f"{user}\n\nRespond with valid JSON matching this schema:\n{schema_str}"
        response = self._client.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()
        raw = str(response.json()["message"]["content"])
        return _extract_json(raw)
