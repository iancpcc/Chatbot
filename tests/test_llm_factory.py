import pytest

from app.domain.exceptions import InfrastructureError
from app.infrastructure.providers.llm.factory import create_llm_client
from app.infrastructure.providers.llm.groq_client import GroqClient
from app.infrastructure.providers.llm.ollama_client import OllamaClient
from app.infrastructure.providers.llm.openai_client import OpenAIClient


def test_llm_factory_defaults_to_ollama_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("APP_ENV", "dev")
    assert isinstance(create_llm_client(), OllamaClient)


def test_llm_factory_selects_groq_in_staging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")
    assert isinstance(create_llm_client(), GroqClient)


def test_llm_factory_selects_openai_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("APP_ENV", "prod")
    assert isinstance(create_llm_client(), OpenAIClient)


def test_llm_factory_allows_provider_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert isinstance(create_llm_client(), OllamaClient)


def test_llm_factory_rejects_unknown_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("APP_ENV", "weird")
    with pytest.raises(InfrastructureError):
        create_llm_client()


def test_llm_factory_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(InfrastructureError):
        create_llm_client()


def test_llm_factory_does_not_require_keys_at_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Construction is lazy; the actual network call happens on generate_reply().
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    create_llm_client()

    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    create_llm_client()


def test_ollama_client_uses_local_fallback_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    client = OllamaClient()
    assert client._api_key == "ollama"


def test_ollama_client_uses_explicit_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "ollama-secret-key")
    client = OllamaClient()
    assert client._api_key == "ollama-secret-key"
