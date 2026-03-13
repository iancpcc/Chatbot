import re
from unittest.mock import Mock
from uuid import UUID

from fastapi.testclient import TestClient

from app.application.use_cases.respond_to_message import RespondToMessage
from app.infrastructure.persistence.sqlalchemy_conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.main import app
from app.presentation.http.dependencies import (
    get_cancel_booking_use_case,
    get_create_booking_use_case,
    get_list_bookings_use_case,
    get_list_resources_use_case,
    get_list_services_use_case,
    get_respond_to_message_use_case,
    reset_state,
)

API_PREFIX = "/v1"
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


def _create_service(client: TestClient, tenant_id: str, name: str = "Corte") -> str:
    response = client.post(
        f"{API_PREFIX}/services",
        json={
            "tenant_id": tenant_id,
            "name": name,
            "duration_minutes": 30,
            "price": 20.0,
        },
    )
    assert response.status_code == 200
    return response.json()["service_id"]


def _create_resource(client: TestClient, tenant_id: str, name: str = "Silla 1") -> str:
    response = client.post(
        f"{API_PREFIX}/resources",
        json={
            "tenant_id": tenant_id,
            "name": name,
        },
    )
    assert response.status_code == 200
    return response.json()["resource_id"]


def _override_chat_use_case_with_transactional_mock_llm() -> None:
    mock_llm = Mock()
    mock_llm.generate_reply.side_effect = AssertionError(
        "LLM should not be called for transactional booking flow"
    )
    use_case = RespondToMessage(
        conversation_repository=SqlAlchemyConversationRepository(),
        llm_client=mock_llm,
        create_booking_use_case=get_create_booking_use_case(),
        cancel_booking_use_case=get_cancel_booking_use_case(),
        list_bookings_use_case=get_list_bookings_use_case(),
        list_services_use_case=get_list_services_use_case(),
        list_resources_use_case=get_list_resources_use_case(),
    )
    app.dependency_overrides[get_respond_to_message_use_case] = lambda: use_case


def test_http_chat_can_create_and_cancel_booking_transactionally() -> None:
    reset_state()
    _override_chat_use_case_with_transactional_mock_llm()
    tenant_id = "tenant-chat-tx-1"

    with TestClient(app) as client:
        service_id = _create_service(client, tenant_id)
        resource_id = _create_resource(client, tenant_id)

        preconfirm_response = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-1",
                "channel": "web",
                "message": (
                    "quiero reservar "
                    f"servicio={service_id}, "
                    f"recurso={resource_id}, "
                    "inicio=2026-03-20T10:00:00Z, "
                    "nombre=Ana Perez, "
                    "contacto=+34123456789"
                ),
            },
        )

        assert preconfirm_response.status_code == 200
        preconfirm_payload = preconfirm_response.json()
        assert preconfirm_payload["response"]["type"] == "confirmation"
        assert "Confirma tu reserva" in preconfirm_payload["reply"]

        create_response = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-1",
                "channel": "web",
                "conversation_id": preconfirm_payload["conversation_id"],
                "message": "confirmar",
                "action_id": "confirm",
            },
        )

        assert create_response.status_code == 200
        create_payload = create_response.json()
        assert "Reserva confirmada" in create_payload["reply"]

        match = UUID_PATTERN.search(create_payload["reply"])
        assert match is not None
        booking_id = UUID(match.group(0))

        cancel_response = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-1",
                "channel": "web",
                "conversation_id": preconfirm_payload["conversation_id"],
                "message": f"cancelar reserva {booking_id}",
            },
        )
        assert cancel_response.status_code == 200
        assert "cancelada correctamente" in cancel_response.json()["reply"]

        get_response = client.get(
            f"{API_PREFIX}/bookings/{booking_id}",
            params={"tenant_id": tenant_id},
        )
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "cancelled"

    app.dependency_overrides.clear()


def test_http_chat_booking_slot_filling_across_turns() -> None:
    reset_state()
    _override_chat_use_case_with_transactional_mock_llm()
    tenant_id = "tenant-chat-tx-2"

    with TestClient(app) as client:
        service_id = _create_service(client, tenant_id)
        resource_id = _create_resource(client, tenant_id)

        first = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-2",
                "channel": "web",
                "message": "Quiero reservar una cita",
            },
        )
        assert first.status_code == 200
        assert first.json()["response"]["type"] == "options"
        assert "Selecciona un servicio" in first.json()["reply"]

        second = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-2",
                "channel": "web",
                "conversation_id": first.json()["conversation_id"],
                "message": f"servicio={service_id}, recurso={resource_id}",
            },
        )
        assert second.status_code == 200
        assert second.json()["response"]["type"] == "options"
        assert "Selecciona un horario" in second.json()["reply"]

        third = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-2",
                "channel": "web",
                "conversation_id": first.json()["conversation_id"],
                "message": (
                    "mañana a las 10, nombre=Carlos Lopez, "
                    "contacto=+34999999999"
                ),
            },
        )
        assert third.status_code == 200
        assert third.json()["response"]["type"] == "confirmation"
        assert "Confirma tu reserva" in third.json()["reply"]

        fourth = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-2",
                "channel": "web",
                "conversation_id": first.json()["conversation_id"],
                "message": "confirmar",
                "action_id": "confirm",
            },
        )
        assert fourth.status_code == 200
        assert "Reserva confirmada" in fourth.json()["reply"]

    app.dependency_overrides.clear()


def test_http_chat_selects_suggested_slot_via_action_id() -> None:
    reset_state()
    _override_chat_use_case_with_transactional_mock_llm()
    tenant_id = "tenant-chat-tx-3"

    with TestClient(app) as client:
        service_id = _create_service(client, tenant_id, name="Masaje")
        _create_resource(client, tenant_id, name="Sala 2")

        first = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-3",
                "channel": "web",
                "message": f"reservar servicio={service_id}",
            },
        )
        assert first.status_code == 200
        payload = first.json()
        assert payload["response"]["type"] == "options"
        assert payload["response"]["options"]
        slot_action_id = payload["response"]["options"][0]["id"]

        second = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-3",
                "channel": "web",
                "conversation_id": payload["conversation_id"],
                "message": "",
                "action_id": slot_action_id,
            },
        )
        assert second.status_code == 200
        assert second.json()["response"]["type"] == "text"
        assert "Necesito tu nombre" in second.json()["reply"]

    app.dependency_overrides.clear()


def test_http_chat_asks_resource_only_when_multiple_are_available() -> None:
    reset_state()
    _override_chat_use_case_with_transactional_mock_llm()
    tenant_id = "tenant-chat-tx-4"

    with TestClient(app) as client:
        service_id = _create_service(client, tenant_id, name="Manicure")
        resource_a = _create_resource(client, tenant_id, name="Mesa 1")
        _create_resource(client, tenant_id, name="Mesa 2")

        first = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-4",
                "channel": "web",
                "message": (
                    "quiero reservar "
                    f"servicio={service_id}, "
                    "inicio=2030-03-20T10:00:00Z, "
                    "nombre=Ana Perez, "
                    "contacto=+34123456789"
                ),
            },
        )
        assert first.status_code == 200
        first_payload = first.json()
        assert first_payload["response"]["type"] == "options"
        assert "varios recursos disponibles" in first_payload["reply"]

        second = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-4",
                "channel": "web",
                "conversation_id": first_payload["conversation_id"],
                "message": "",
                "action_id": resource_a,
            },
        )
        assert second.status_code == 200
        assert second.json()["response"]["type"] == "confirmation"

    app.dependency_overrides.clear()


def test_http_chat_stops_booking_when_no_resources_configured() -> None:
    reset_state()
    _override_chat_use_case_with_transactional_mock_llm()
    tenant_id = "tenant-chat-tx-5"

    with TestClient(app) as client:
        service_id = _create_service(client, tenant_id, name="Manicure")

        response = client.post(
            f"{API_PREFIX}/chat",
            json={
                "tenant_id": tenant_id,
                "user_id": "user-tx-5",
                "channel": "web",
                "message": (
                    "quiero reservar "
                    f"servicio={service_id}, "
                    "inicio=2030-03-20T11:00:00Z, "
                    "nombre=Ana Perez, "
                    "contacto=+34123456789"
                ),
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["response"]["type"] == "text"
        assert "No hay recursos disponibles" in payload["reply"]

    app.dependency_overrides.clear()
