from cliniq.adapters.base import LLMAdapter
from cliniq.adapters.claude import ClaudeAdapter
from cliniq.adapters.ollama import OllamaAdapter


def get_adapter(backend: str) -> LLMAdapter:
    match backend:
        case "ollama":
            return OllamaAdapter()
        case "claude":
            return ClaudeAdapter()
        case _:
            raise NotImplementedError(f"Adapter not yet implemented: {backend}")


__all__ = ["LLMAdapter", "OllamaAdapter", "ClaudeAdapter", "get_adapter"]
