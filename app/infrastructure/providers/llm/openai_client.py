import os
from typing import Any, cast

from openai import OpenAI

from app.application.ports.llm_client import LLMClient
from app.domain.exceptions import InfrastructureError


class OpenAIClient(LLMClient):
    def __init__(self) -> None:
        # Do not fail at import/startup. We fail when the endpoint is used so the
        # API can still start for non-chat endpoints.
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        self._model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self._client: OpenAI | None = None

    def generate_reply(self, *, messages: list[dict[str, str]]) -> str:
        if not self._api_key or self._api_key == "your_key_here":
            raise InfrastructureError("OPENAI_API_KEY is not configured")

        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)

        # OpenAI Python SDK v2: use Chat Completions for simple conversational replies.
        response = self._client.chat.completions.create(
            model=self._model,
            # SDK expects a typed structure; we validate our own shape upstream.
            messages=cast(Any, messages),
            temperature=0.2,
        )

        choice = response.choices[0]
        content = getattr(choice.message, "content", None)
        if not content:
            raise InfrastructureError("Empty response from LLM")
        return content
