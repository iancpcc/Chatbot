from __future__ import annotations

from datetime import datetime, timezone

from app.application.dto.respond_to_message_dto import (
    RespondToMessageRequest,
    RespondToMessageResponse,
)
from app.application.ports.llm_client import LLMClient
from app.domain.entities.conversation import Conversation
from app.domain.exceptions import InfrastructureError, NotFoundError, ValidationError
from app.domain.repositories.conversation_repository import ConversationRepository


_SYSTEM_PROMPT = (
    "You are a helpful booking assistant. Ask clarifying questions when needed. "
    "When you don't have enough information, ask for it instead of guessing."
)


class RespondToMessage:
    def __init__(self, conversation_repository: ConversationRepository, llm_client: LLMClient):
        self.conversation_repository = conversation_repository
        self.llm_client = llm_client

    def execute(self, request: RespondToMessageRequest) -> RespondToMessageResponse:
        if not request.message or not request.message.strip():
            raise ValidationError("Message must not be empty")

        conversation = self._load_or_create_conversation(request)
        self._append_message(conversation, role="user", content=request.message.strip())
        self.conversation_repository.save(conversation)

        llm_messages = self._build_llm_messages(conversation)
        try:
            reply = self.llm_client.generate_reply(messages=llm_messages)
        except InfrastructureError:
            raise
        except Exception as exc:
            # Keep infra failures from leaking as unhandled 500s without request_id.
            raise InfrastructureError(str(exc)) from exc

        self._append_message(conversation, role="assistant", content=reply)
        self.conversation_repository.save(conversation)

        return RespondToMessageResponse(conversation_id=conversation.id, reply=reply)

    def _load_or_create_conversation(self, request: RespondToMessageRequest) -> Conversation:
        if request.conversation_id is None:
            return Conversation(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                channel=request.channel,
                state={"messages": []},
            )

        conversation = self.conversation_repository.get(request.conversation_id)
        if conversation is None or conversation.tenant_id != request.tenant_id:
            raise NotFoundError("Conversation not found")
        return conversation

    def _append_message(self, conversation: Conversation, *, role: str, content: str) -> None:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        existing = conversation.state.get("messages", [])
        if not isinstance(existing, list):
            raise ValidationError("Conversation state is corrupted (messages)")

        # Replace the list to ensure SQLAlchemy JSON change tracking sees the update.
        messages = list(existing)
        messages.append({"role": role, "content": content, "at": now})
        conversation.state["messages"] = messages

    def _build_llm_messages(self, conversation: Conversation) -> list[dict[str, str]]:
        raw_messages = conversation.state.get("messages", [])
        if not isinstance(raw_messages, list):
            raw_messages = []

        # Keep the prompt size bounded for MVP.
        history = raw_messages[-20:]

        messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str):
                messages.append({"role": role, "content": content})
        return messages
