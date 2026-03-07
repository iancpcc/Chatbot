from unittest.mock import Mock
from uuid import UUID

from fastapi.testclient import TestClient

from app.application.use_cases.respond_to_message import RespondToMessage
from app.infrastructure.persistence.sqlalchemy_conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.main import app
from app.presentation.http.dependencies import get_respond_to_message_use_case, reset_state


def test_http_chat_creates_and_persists_conversation() -> None:
    reset_state()

    conversation_repo = SqlAlchemyConversationRepository()
    mock_llm = Mock()
    mock_llm.generate_reply.side_effect = ["Respuesta 1", "Respuesta 2"]

    use_case = RespondToMessage(conversation_repository=conversation_repo, llm_client=mock_llm)
    app.dependency_overrides[get_respond_to_message_use_case] = lambda: use_case

    with TestClient(app) as client:
        first = client.post(
            "/v1/chat",
            json={
                "tenant_id": "tenant-chat-1",
                "user_id": "user-1",
                "channel": "web",
                "message": "Hola",
            },
        )
        assert first.status_code == 200
        data1 = first.json()
        assert data1["reply"] == "Respuesta 1"

        conversation_id = UUID(data1["conversation_id"])
        stored = conversation_repo.get(conversation_id)
        assert stored is not None
        assert stored.tenant_id == "tenant-chat-1"
        assert len(stored.state["messages"]) == 2
        assert stored.state["messages"][0]["role"] == "user"
        assert stored.state["messages"][1]["role"] == "assistant"

        second = client.post(
            "/v1/chat",
            json={
                "tenant_id": "tenant-chat-1",
                "user_id": "user-1",
                "channel": "web",
                "conversation_id": str(conversation_id),
                "message": "Otra pregunta",
            },
        )
        assert second.status_code == 200
        data2 = second.json()
        assert data2["conversation_id"] == str(conversation_id)
        assert data2["reply"] == "Respuesta 2"

        stored2 = conversation_repo.get(conversation_id)
        assert stored2 is not None
        assert len(stored2.state["messages"]) == 4

    app.dependency_overrides.clear()

