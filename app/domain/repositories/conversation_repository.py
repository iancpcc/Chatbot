from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities.conversation import Conversation


class ConversationRepository(ABC):
    @abstractmethod
    def save(self, conversation: Conversation) -> None:
        pass

    @abstractmethod
    def get(self, conversation_id: UUID) -> Optional[Conversation]:
        pass
