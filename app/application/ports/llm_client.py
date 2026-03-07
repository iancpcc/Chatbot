from typing import Protocol


class LLMClient(Protocol):
    def generate_reply(self, *, messages: list[dict[str, str]]) -> str:
        """Return an assistant reply given a list of chat messages.

        Each message is expected to be a dict with keys: role, content.
        """

