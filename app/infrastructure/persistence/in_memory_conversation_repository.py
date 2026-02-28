from typing import Optional
from uuid import UUID

from app.domain.entities.conversation import Conversation
from app.domain.repositories.conversation_repository import ConversationRepository


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self) -> None:
        self._storage: dict[UUID, Conversation] = {}

    def save(self, conversation: Conversation) -> None:
        self._storage[conversation.id] = conversation

    def get(self, conversation_id: UUID) -> Optional[Conversation]:
        return self._storage.get(conversation_id)
