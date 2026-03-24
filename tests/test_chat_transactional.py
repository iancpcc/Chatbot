from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import UUID

from app.application.dto.respond_to_message_dto import RespondToMessageRequest
from app.application.use_cases.cancel_booking import CancelBooking
from app.application.use_cases.create_booking import CreateBooking
from app.application.use_cases.list_bookings import ListBookings
from app.application.use_cases.list_resources import ListResources
from app.application.use_cases.list_services import ListServices
from app.application.use_cases.respond_to_message import RespondToMessage
from app.infrastructure.persistence.in_memory_booking_repository import (
    InMemoryBookingRepository,
)
from app.infrastructure.persistence.in_memory_conversation_repository import (
    InMemoryConversationRepository,
)
from app.infrastructure.persistence.in_memory_resource_repository import (
    InMemoryResourceRepository,
)
from app.infrastructure.persistence.in_memory_service_repository import (
    InMemoryServiceRepository,
)
from app.domain.entities.resource import Resource
from app.domain.entities.service import Service
from app.domain.entities.booking import Booking
from app.domain.entities.customer import Customer
from app.domain.value_objects.time_slot import TimeSlot


def _build_transactional_use_case() -> tuple[
    RespondToMessage,
    InMemoryConversationRepository,
    InMemoryBookingRepository,
    InMemoryServiceRepository,
    InMemoryResourceRepository,
]:
    conversation_repo = InMemoryConversationRepository()
    booking_repo = InMemoryBookingRepository()
    service_repo = InMemoryServiceRepository()
    resource_repo = InMemoryResourceRepository()
    mock_llm = Mock()
    mock_llm.generate_reply.side_effect = AssertionError(
        "LLM should not be called for transactional booking flow"
    )

    use_case = RespondToMessage(
        conversation_repository=conversation_repo,
        llm_client=mock_llm,
        create_booking_use_case=CreateBooking(
            booking_repository=booking_repo,
            service_repository=service_repo,
            resource_repository=resource_repo,
        ),
        cancel_booking_use_case=CancelBooking(booking_repo),
        list_bookings_use_case=ListBookings(booking_repo),
        list_services_use_case=ListServices(service_repo),
        list_resources_use_case=ListResources(resource_repo),
    )
    return use_case, conversation_repo, booking_repo, service_repo, resource_repo


def test_chat_can_create_and_cancel_booking_transactionally() -> None:
    use_case, conversation_repo, booking_repo, service_repo, resource_repo = (
        _build_transactional_use_case()
    )
    tenant_id = "tenant-chat-tx-1"
    service = Service(name="Corte", duration_minutes=30, price=20.0)
    resource = Resource(name="Silla 1")
    service_repo.save(tenant_id, service)
    resource_repo.save(tenant_id, resource)

    first = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-1",
            channel="web",
            message="Hola",
        )
    )
    assert first.response is not None
    assert first.response.type == "options"
    assert "Nails Studio" in first.reply
    assert first.response.options is not None
    assert any(option.label == "Chatear con asistente" for option in first.response.options)

    second = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-1",
            channel="web",
            conversation_id=first.conversation_id,
            message="1",
        )
    )
    assert second.response is not None
    assert "¿Qué servicio deseas?" in second.reply

    third = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-1",
            channel="web",
            conversation_id=first.conversation_id,
            message="1",
        )
    )
    assert third.response is not None
    assert "Selecciona una fecha" in third.reply

    fourth = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-1",
            channel="web",
            conversation_id=first.conversation_id,
            message="1",
        )
    )
    assert fourth.response is not None
    assert "Disponibilidad para mañana" in fourth.reply
    assert fourth.response.options

    fifth = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-1",
            channel="web",
            conversation_id=first.conversation_id,
            message="1",
            action_id=fourth.response.options[0].id,
        )
    )
    assert fifth.response is not None
    assert "Ahora necesito tu nombre" in fifth.reply

    preconfirm = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-1",
            channel="web",
            conversation_id=first.conversation_id,
            message="Ana Perez",
        )
    )

    assert preconfirm.response is not None
    assert preconfirm.response.type == "options"
    assert "¿Deseas confirmar tu cita?" in preconfirm.reply

    created = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-1",
            channel="web",
            conversation_id=first.conversation_id,
            message="1",
        )
    )
    assert "Reserva confirmada" in created.reply

    stored_conversation = conversation_repo.get(first.conversation_id)
    assert stored_conversation is not None
    booking_id = UUID(str(stored_conversation.state["last_booking_id"]))
    stored_booking = booking_repo.get_by_id(booking_id)
    assert stored_booking is not None
    assert stored_booking.status.value == "pending"

    cancelled = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-1",
            channel="web",
            conversation_id=first.conversation_id,
            message=f"cancelar reserva {booking_id}",
        )
    )
    assert "cancelada correctamente" in cancelled.reply

    updated_booking = booking_repo.get_by_id(booking_id)
    assert updated_booking is not None
    assert updated_booking.status.value == "cancelled"


def test_chat_fills_booking_slots_across_turns() -> None:
    use_case, _, _, service_repo, resource_repo = _build_transactional_use_case()
    tenant_id = "tenant-chat-tx-2"
    service = Service(name="Corte", duration_minutes=30, price=20.0)
    resource = Resource(name="Silla 1")
    service_repo.save(tenant_id, service)
    resource_repo.save(tenant_id, resource)

    first = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-2",
            channel="web",
            message="Quiero reservar una cita",
        )
    )
    assert first.response is not None
    assert first.response.type == "options"
    assert "¿Qué servicio deseas?" in first.reply


def test_dates_without_availability_are_hidden() -> None:
    use_case, _, booking_repo, service_repo, resource_repo = _build_transactional_use_case()
    tenant_id = "tenant-chat-no-availability"
    service = Service(name="Corte", duration_minutes=30, price=20.0)
    resource = Resource(name="Silla 1")
    service_repo.save(tenant_id, service)
    resource_repo.save(tenant_id, resource)

    today = datetime.now(timezone.utc).date()
    for day_offset in range(0, 2):
        for hour in range(10, 20):
            start = datetime(
                year=today.year,
                month=today.month,
                day=(today + timedelta(days=day_offset)).day,
                hour=hour,
                minute=0,
                tzinfo=timezone.utc,
            )
            booking_repo.save(
                Booking(
                    tenant_id=tenant_id,
                    service=service,
                    resource=resource,
                    customer=Customer(full_name="Blocked", contact="x"),
                    time_slot=TimeSlot(start=start, end=start + timedelta(minutes=30)),
                )
            )

    first = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-no-availability",
            channel="web",
            message="Hola",
        )
    )
    second = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-no-availability",
            channel="web",
            conversation_id=first.conversation_id,
            message="1",
        )
    )
    third = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-no-availability",
            channel="web",
            conversation_id=first.conversation_id,
            message="1",
        )
    )

    assert second.response is not None
    assert third.response is not None
    assert second.response.options is not None
    assert all("0 disponibles" not in option.label for option in second.response.options)


def test_chat_detects_booking_intent_from_free_text() -> None:
    use_case, _, _, service_repo, resource_repo = _build_transactional_use_case()
    tenant_id = "tenant-chat-intent"
    service_repo.save(tenant_id, Service(name="Corte", duration_minutes=30, price=20.0))
    resource_repo.save(tenant_id, Resource(name="Silla 1"))

    response = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-intent",
            channel="web",
            message="quiero cita",
        )
    )

    assert response.response is not None
    assert response.response.type == "options"
    assert "¿Qué servicio deseas?" in response.reply


def test_chat_enters_assistant_mode_from_menu_option() -> None:
    use_case, _, _, service_repo, resource_repo = _build_transactional_use_case()
    tenant_id = "tenant-chat-assistant"
    service_repo.save(tenant_id, Service(name="Corte", duration_minutes=30, price=20.0))
    resource_repo.save(tenant_id, Resource(name="Silla 1"))

    first = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-assistant",
            channel="web",
            message="Hola",
        )
    )
    assert first.response is not None
    assert first.response.options is not None
    assistant_option = next(
        option for option in first.response.options if option.id == "assistant_chat"
    )
    assert assistant_option.label == "Chatear con asistente"

    second = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-assistant",
            channel="web",
            conversation_id=first.conversation_id,
            message="4",
        )
    )
    assert second.response is not None
    assert "Estás hablando con el asistente" in second.reply

    third = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-assistant",
            channel="web",
            conversation_id=first.conversation_id,
            message="menu",
        )
    )
    assert third.response is not None
    assert third.response.type == "options"
    assert "¿En qué puedo ayudarte?" in third.reply
    assert third.response.options is not None
    assert any(option.label == "Chatear con asistente" for option in third.response.options)


def test_chat_back_command_returns_to_main_menu() -> None:
    use_case, _, _, service_repo, resource_repo = _build_transactional_use_case()
    tenant_id = "tenant-chat-back"
    service_repo.save(tenant_id, Service(name="Corte", duration_minutes=30, price=20.0))
    resource_repo.save(tenant_id, Resource(name="Silla 1"))

    first = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-back",
            channel="web",
            message="Hola",
        )
    )
    second = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-back",
            channel="web",
            conversation_id=first.conversation_id,
            message="1",
        )
    )
    assert second.response is not None
    assert second.response.type == "options"

    third = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-back",
            channel="web",
            conversation_id=first.conversation_id,
            message="volver",
        )
    )
    assert third.response is not None
    assert third.response.type == "options"
    assert "¿En qué puedo ayudarte?" in third.reply
    assert third.response.options is not None
    assert any(option.label == "Chatear con asistente" for option in third.response.options)


def test_submenu_exposes_back_option() -> None:
    use_case, _, _, service_repo, resource_repo = _build_transactional_use_case()
    tenant_id = "tenant-chat-back-option"
    service_repo.save(tenant_id, Service(name="Corte", duration_minutes=30, price=20.0))
    resource_repo.save(tenant_id, Resource(name="Silla 1"))

    first = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-back-option",
            channel="web",
            message="Hola",
        )
    )
    second = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-back-option",
            channel="web",
            conversation_id=first.conversation_id,
            message="1",
        )
    )

    assert second.response is not None
    assert second.response.options is not None
    assert any(option.label == "Volver" for option in second.response.options)

    back_option = next(option for option in second.response.options if option.label == "Volver")
    third = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-back-option",
            channel="web",
            conversation_id=first.conversation_id,
            message="",
            action_id=back_option.id,
        )
    )

    assert third.response is not None
    assert third.response.type == "options"
    assert "¿En qué puedo ayudarte?" in third.reply



def test_chat_selects_suggested_slot_via_action_id() -> None:
    use_case, _, _, service_repo, resource_repo = _build_transactional_use_case()
    tenant_id = "tenant-chat-tx-3"
    service = Service(name="Masaje", duration_minutes=30, price=35.0)
    resource = Resource(name="Sala 2")
    service_repo.save(tenant_id, service)
    resource_repo.save(tenant_id, resource)

    first = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-3",
            channel="web",
            message=f"reservar servicio={service.id}",
        )
    )
    assert first.response is not None
    assert first.response.type == "options"
    assert "Selecciona una fecha" in first.reply
    assert first.response.options

    second = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-3",
            channel="web",
            conversation_id=first.conversation_id,
            message="1",
        )
    )
    assert second.response is not None
    assert second.response.type == "options"
    assert second.response.options
    assert "mañana" in second.reply.lower()

    third = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-3",
            channel="web",
            conversation_id=first.conversation_id,
            message="",
            action_id=second.response.options[0].id,
        )
    )
    assert third.response is not None
    assert third.response.type == "text"
    assert "Ahora necesito tu nombre" in third.reply


def test_chat_asks_resource_only_when_multiple_are_available() -> None:
    use_case, _, _, service_repo, resource_repo = _build_transactional_use_case()
    tenant_id = "tenant-chat-tx-4"
    service = Service(name="Manicure", duration_minutes=30, price=25.0)
    resource_a = Resource(name="Mesa 1")
    resource_b = Resource(name="Mesa 2")
    service_repo.save(tenant_id, service)
    resource_repo.save(tenant_id, resource_a)
    resource_repo.save(tenant_id, resource_b)

    first = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-4",
            channel="web",
            message=(
                "quiero reservar "
                f"servicio={service.id}, "
                "mañana a las 10, "
                "nombre=Ana Perez"
            ),
        )
    )
    assert first.response is not None
    assert first.response.type == "options"
    assert "varios recursos disponibles" in first.reply

    second = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-4",
            channel="web",
            conversation_id=first.conversation_id,
            message="",
            action_id=str(resource_a.id),
        )
    )
    assert second.response is not None
    assert second.response.type == "options"


def test_chat_stops_booking_when_no_resources_configured() -> None:
    use_case, _, _, service_repo, _ = _build_transactional_use_case()
    tenant_id = "tenant-chat-tx-5"
    service = Service(name="Manicure", duration_minutes=30, price=25.0)
    service_repo.save(tenant_id, service)

    response = use_case.execute(
        RespondToMessageRequest(
            tenant_id=tenant_id,
            user_id="user-tx-5",
            channel="web",
            message=(
                "quiero reservar "
                f"servicio={service.id}, "
                "inicio=2030-03-20T11:00:00Z, "
                "nombre=Ana Perez"
            ),
        )
    )
    assert response.response is not None
    assert response.response.type == "text"
    assert "No hay recursos disponibles" in response.reply
