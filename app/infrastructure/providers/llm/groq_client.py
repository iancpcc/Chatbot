import os
from typing import Any, cast

from openai import OpenAI

from app.application.ports.llm_client import LLMClient
from app.domain.exceptions import InfrastructureError


class GroqClient(LLMClient):
    def __init__(self) -> None:
        # Groq exposes an OpenAI-compatible API surface.
        self._api_key = os.getenv("GROQ_API_KEY", "")
        self._model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self._base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        self._client: OpenAI | None = None

    def generate_reply(self, *, messages: list[dict[str, str]]) -> str:
        if not self._api_key:
            raise InfrastructureError("GROQ_API_KEY is not configured")

        if self._client is None:
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)

        response = self._client.chat.completions.create(
            model=self._model,
            messages=cast(Any, messages),
            temperature=0.2,
        )

        choice = response.choices[0]
        content = getattr(choice.message, "content", None)
        if not content:
            raise InfrastructureError("Empty response from LLM (groq)")
        return content

