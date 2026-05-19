"""Anthropic Claude adapter."""

from __future__ import annotations

import json
import os
from typing import Any

from cliniq.adapters.base import LLMAdapter

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 4096


class ClaudeAdapter(LLMAdapter):
    def __init__(self, model: str = _DEFAULT_MODEL, api_key: str | None = None) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package required: uv pip install 'cliniq[claude]'"
            ) from exc
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = anthropic.Anthropic(api_key=key)
        self.model = model

    def complete(self, system: str, user: str) -> str:
        import anthropic

        message = self._client.messages.create(
            model=self.model,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        block = message.content[0]
        if not isinstance(block, anthropic.types.TextBlock):
            raise ValueError(f"unexpected content block type: {type(block)}")
        return str(block.text)

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> Any:
        schema_str = json.dumps(schema, indent=2)
        prompt = f"{user}\n\nRespond with valid JSON matching this schema:\n{schema_str}"
        raw = self.complete(system=system, user=prompt)
        stripped = raw.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            stripped = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
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
        return json.loads(stripped[start:end])
