import os
from typing import Any, cast

from openai import OpenAI

from app.application.ports.llm_client import LLMClient
from app.domain.exceptions import InfrastructureError


class OllamaClient(LLMClient):
    def __init__(self) -> None:
        # Ollama offers an OpenAI-compatible API at /v1.
        # Local deployments usually do not require a real key, so we keep a safe
        # default token for local compatibility and allow override for hosted APIs.
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self._api_key = os.getenv("OLLAMA_API_KEY") or "ollama"
        self._model = os.getenv("OLLAMA_MODEL", "llama3.1")
        self._client = OpenAI(
            base_url=base_url,
            api_key=self._api_key,
        )

    def generate_reply(self, *, messages: list[dict[str, str]]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=cast(Any, messages),
                temperature=0.2,
            )
        except Exception as exc:
            raise InfrastructureError(f"Ollama request failed: {exc}") from exc

        choice = response.choices[0]
        content = getattr(choice.message, "content", None)
        if not content:
            raise InfrastructureError("Empty response from LLM (ollama)")
        return content
