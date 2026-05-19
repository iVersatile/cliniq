"""Ollama adapter — default local backend (CPU-only)."""

from __future__ import annotations

import json
from typing import Any

import httpx

from cliniq.adapters.base import LLMAdapter

_DEFAULT_MODEL = "phi3:mini"
_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaAdapter(LLMAdapter):
    def __init__(self, model: str = _DEFAULT_MODEL, base_url: str = _DEFAULT_BASE_URL) -> None:
        self.model = model
        self.base_url = base_url

    def complete(self, system: str, user: str) -> str:
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        return str(response.json()["message"]["content"])

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        schema_str = json.dumps(schema, indent=2)
        prompt = f"{user}\n\nRespond with valid JSON matching this schema:\n{schema_str}"
        raw = self.complete(system=system, user=prompt)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        result: dict[str, Any] = json.loads(raw[start:end])
        return result
