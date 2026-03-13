from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    tenant_id: str
    user_id: str
    channel: str
    message: str
    conversation_id: UUID | None = None
    action_id: str | None = None


class ChatResponseOption(BaseModel):
    id: str
    label: str


class ChatResponsePayload(BaseModel):
    type: str
    message: str
    text: str | None = None
    options: list[ChatResponseOption] | None = None
    confirm_label: str | None = None
    cancel_label: str | None = None


class ChatResponse(BaseModel):
    conversation_id: UUID
    reply: str
    response: ChatResponsePayload | None = None
