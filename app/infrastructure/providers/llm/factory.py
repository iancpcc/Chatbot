import os

from app.application.ports.llm_client import LLMClient
from app.domain.exceptions import InfrastructureError
from app.infrastructure.providers.llm.groq_client import GroqClient
from app.infrastructure.providers.llm.ollama_client import OllamaClient
from app.infrastructure.providers.llm.openai_client import OpenAIClient


def create_llm_client() -> LLMClient:
    """Select LLM provider by environment.

    Intended mapping:
    - dev local  -> Ollama
    - staging    -> Groq
    - production -> OpenAI

    You can override the mapping with `LLM_PROVIDER=ollama|groq|openai`.
    """

    provider = resolve_llm_provider()
    return _from_provider(provider)


def resolve_llm_provider() -> str:
    provider = os.getenv("LLM_PROVIDER")
    if provider:
        normalized = provider.strip().lower()
        if normalized in {"ollama", "groq", "openai"}:
            return normalized
        raise InfrastructureError(f"Unsupported LLM_PROVIDER={provider!r}")

    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    if app_env == "dev":
        return "ollama"
    if app_env == "staging":
        return "groq"
    if app_env in ("prod", "production"):
        return "openai"

    raise InfrastructureError(f"Unsupported APP_ENV={app_env!r}")


def _from_provider(provider: str) -> LLMClient:
    normalized = provider.strip().lower()
    if normalized == "ollama":
        return OllamaClient()
    if normalized == "groq":
        return GroqClient()
    if normalized == "openai":
        return OpenAIClient()
    raise InfrastructureError(f"Unsupported LLM_PROVIDER={provider!r}")
