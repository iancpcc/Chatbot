from uuid import UUID

from app.infrastructure.persistence.in_memory_booking_repository import (
    InMemoryBookingRepository,
)
from app.infrastructure.persistence.in_memory_service_repository import (
    InMemoryServiceRepository,
)
from app.infrastructure.persistence.in_memory_resource_repository import (
    InMemoryResourceRepository,
)
from app.application.use_cases.create_booking import CreateBooking
from app.application.use_cases.cancel_booking import CancelBooking
from app.domain.entities.resource import Resource
from app.domain.entities.service import Service

_booking_repository = InMemoryBookingRepository()
_service_repository = InMemoryServiceRepository()
_resource_repository = InMemoryResourceRepository()

DEMO_TENANT_ID = "demo-salon"
DEMO_SERVICE_ID = UUID("11111111-1111-1111-1111-111111111111")
DEMO_RESOURCE_ID = UUID("22222222-2222-2222-2222-222222222222")

_service_repository.save(
    tenant_id=DEMO_TENANT_ID,
    service=Service(
        id=DEMO_SERVICE_ID,
        name="Corte de cabello",
        duration_minutes=30,
        price=20.0,
    ),
)
_resource_repository.save(
    tenant_id=DEMO_TENANT_ID,
    resource=Resource(
        id=DEMO_RESOURCE_ID,
        name="Silla 1",
    ),
)

_create_booking = CreateBooking(
    booking_repository=_booking_repository,
    service_repository=_service_repository,
    resource_repository=_resource_repository,
)
_cancel_booking = CancelBooking(_booking_repository)


def get_create_booking_use_case() -> CreateBooking:
    return _create_booking


def get_cancel_booking_use_case() -> CancelBooking:
    return _cancel_booking
