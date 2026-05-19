"""Abstract LLM adapter — any backend must implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMAdapter(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Send a prompt and return the raw text response."""

    @abstractmethod
    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> Any:
        """Send a prompt and return a validated JSON response matching schema."""
