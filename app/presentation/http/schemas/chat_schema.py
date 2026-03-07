from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    tenant_id: str
    user_id: str
    channel: str
    message: str
    conversation_id: UUID | None = None


class ChatResponse(BaseModel):
    conversation_id: UUID
    reply: str

