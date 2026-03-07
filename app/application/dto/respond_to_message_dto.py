from dataclasses import dataclass
from uuid import UUID


@dataclass
class RespondToMessageRequest:
    tenant_id: str
    user_id: str
    channel: str
    message: str
    conversation_id: UUID | None = None


@dataclass
class RespondToMessageResponse:
    conversation_id: UUID
    reply: str

