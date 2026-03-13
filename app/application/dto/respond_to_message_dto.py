from dataclasses import dataclass
from uuid import UUID


@dataclass
class RespondToMessageRequest:
    tenant_id: str
    user_id: str
    channel: str
    message: str
    conversation_id: UUID | None = None
    action_id: str | None = None


@dataclass
class ResponseOption:
    id: str
    label: str


@dataclass
class ResponsePayload:
    type: str
    message: str
    options: list[ResponseOption] | None = None
    confirm_label: str | None = None
    cancel_label: str | None = None


@dataclass
class RespondToMessageResponse:
    conversation_id: UUID
    reply: str
    response: ResponsePayload | None = None
