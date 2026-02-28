from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.domain.value_objects.conversation import ConversationStatus, ConversationType


@dataclass
class Conversation:
    tenant_id: str
    user_id: str
    channel: str
    id: UUID = field(default_factory=uuid4)
    status: ConversationStatus = ConversationStatus.ACTIVE
    type: ConversationType = ConversationType.CHAT
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    state: dict = field(default_factory=dict)

    def touch(self) -> None:
        self.started_at = datetime.now(timezone.utc)

    def close(self) -> None:
        self.status = ConversationStatus.CLOSED
        self.ended_at = datetime.now(timezone.utc)
