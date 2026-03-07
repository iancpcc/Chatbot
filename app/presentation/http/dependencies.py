from app.application.use_cases.create_booking import CreateBooking
from app.application.use_cases.cancel_booking import CancelBooking
from app.application.use_cases.create_resource import CreateResource
from app.application.use_cases.create_service import CreateService
from app.application.use_cases.get_booking import GetBooking
from app.application.use_cases.list_bookings import ListBookings
from app.application.use_cases.respond_to_message import RespondToMessage
from app.infrastructure.persistence.bootstrap import init_schema, seed_demo_catalog
from app.infrastructure.persistence.sqlalchemy_booking_repository import (
    SqlAlchemyBookingRepository,
)
from app.infrastructure.persistence.sqlalchemy_conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.infrastructure.persistence.sqlalchemy_resource_repository import (
    SqlAlchemyResourceRepository,
)
from app.infrastructure.persistence.sqlalchemy_service_repository import (
    SqlAlchemyServiceRepository,
)
from app.infrastructure.providers.llm.openai_client import OpenAIClient

_booking_repository: SqlAlchemyBookingRepository
_service_repository: SqlAlchemyServiceRepository
_resource_repository: SqlAlchemyResourceRepository
_conversation_repository: SqlAlchemyConversationRepository
_llm_client: OpenAIClient
_create_booking: CreateBooking
_cancel_booking: CancelBooking
_create_service: CreateService
_create_resource: CreateResource
_list_bookings: ListBookings
_get_booking: GetBooking
_respond_to_message: RespondToMessage


def reset_state() -> None:
    global _booking_repository
    global _service_repository
    global _resource_repository
    global _conversation_repository
    global _llm_client
    global _create_booking
    global _cancel_booking
    global _create_service
    global _create_resource
    global _list_bookings
    global _get_booking
    global _respond_to_message

    init_schema()
    _booking_repository = SqlAlchemyBookingRepository()
    _service_repository = SqlAlchemyServiceRepository()
    _resource_repository = SqlAlchemyResourceRepository()
    _conversation_repository = SqlAlchemyConversationRepository()
    seed_demo_catalog()

    # LLM client is real; it will raise InfrastructureError at call time if missing API key.
    _llm_client = OpenAIClient()

    _create_booking = CreateBooking(
        booking_repository=_booking_repository,
        service_repository=_service_repository,
        resource_repository=_resource_repository,
    )
    _cancel_booking = CancelBooking(_booking_repository)
    _create_service = CreateService(_service_repository)
    _create_resource = CreateResource(_resource_repository)
    _list_bookings = ListBookings(_booking_repository)
    _get_booking = GetBooking(_booking_repository)
    _respond_to_message = RespondToMessage(
        conversation_repository=_conversation_repository,
        llm_client=_llm_client,
    )


def get_create_booking_use_case() -> CreateBooking:
    return _create_booking


def get_cancel_booking_use_case() -> CancelBooking:
    return _cancel_booking


def get_create_service_use_case() -> CreateService:
    return _create_service


def get_create_resource_use_case() -> CreateResource:
    return _create_resource


def get_list_bookings_use_case() -> ListBookings:
    return _list_bookings


def get_get_booking_use_case() -> GetBooking:
    return _get_booking


def get_respond_to_message_use_case() -> RespondToMessage:
    return _respond_to_message
