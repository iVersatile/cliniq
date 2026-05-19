from cliniq.adapters.base import LLMAdapter
from cliniq.adapters.ollama import OllamaAdapter


def get_adapter(backend: str) -> LLMAdapter:
    match backend:
        case "ollama":
            return OllamaAdapter()
        case _:
            raise NotImplementedError(f"Adapter not yet implemented: {backend}")


__all__ = ["LLMAdapter", "OllamaAdapter", "get_adapter"]
