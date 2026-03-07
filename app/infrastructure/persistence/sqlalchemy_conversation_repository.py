from uuid import UUID

from sqlalchemy import select

from app.domain.entities.conversation import Conversation
from app.domain.repositories.conversation_repository import ConversationRepository
from app.domain.value_objects.conversation import ConversationStatus, ConversationType
from app.infrastructure.persistence.sqlalchemy_database import SessionLocal
from app.infrastructure.persistence.sqlalchemy_models import ConversationModel


class SqlAlchemyConversationRepository(ConversationRepository):
    def save(self, conversation: Conversation) -> None:
        with SessionLocal() as session:
            row = session.execute(
                select(ConversationModel).where(ConversationModel.id == str(conversation.id))
            ).scalar_one_or_none()

            if row is None:
                row = ConversationModel(
                    id=str(conversation.id),
                    tenant_id=conversation.tenant_id,
                    user_id=conversation.user_id,
                    channel=conversation.channel,
                    status=conversation.status.value,
                    type=conversation.type.value,
                    started_at=conversation.started_at,
                    ended_at=conversation.ended_at,
                    state=conversation.state,
                )
                session.add(row)
            else:
                # Keep the row aligned with the domain object.
                row.tenant_id = conversation.tenant_id
                row.user_id = conversation.user_id
                row.channel = conversation.channel
                row.status = conversation.status.value
                row.type = conversation.type.value
                row.started_at = conversation.started_at
                row.ended_at = conversation.ended_at
                row.state = conversation.state

            session.commit()

    def get(self, conversation_id: UUID) -> Conversation | None:
        with SessionLocal() as session:
            row = session.execute(
                select(ConversationModel).where(ConversationModel.id == str(conversation_id))
            ).scalar_one_or_none()
            if row is None:
                return None

            # Default to an empty dict so the rest of the app doesn't deal with NULLs.
            state = row.state or {}

            return Conversation(
                id=UUID(row.id),
                tenant_id=row.tenant_id,
                user_id=row.user_id,
                channel=row.channel,
                status=ConversationStatus(row.status),
                type=ConversationType(row.type),
                started_at=row.started_at,
                ended_at=row.ended_at,
                state=state,
            )

