from datetime import datetime, timezone

import pytest

from app.application.dto.create_booking_dto import CreateBookingRequest
from app.application.use_cases.create_booking import CreateBooking
from app.domain.entities.resource import Resource
from app.domain.entities.service import Service
from app.domain.exceptions import ConflictError, NotFoundError
from app.infrastructure.persistence.in_memory_booking_repository import (
    InMemoryBookingRepository,
)
from app.infrastructure.persistence.in_memory_resource_repository import (
    InMemoryResourceRepository,
)
from app.infrastructure.persistence.in_memory_service_repository import (
    InMemoryServiceRepository,
)


def test_create_booking_success() -> None:
    tenant_id = "tenant-a"
    service_repo = InMemoryServiceRepository()
    resource_repo = InMemoryResourceRepository()
    booking_repo = InMemoryBookingRepository()

    service = Service(name="Corte", duration_minutes=30, price=20.0)
    resource = Resource(name="Silla 1")
    service_repo.save(tenant_id, service)
    resource_repo.save(tenant_id, resource)

    use_case = CreateBooking(booking_repo, service_repo, resource_repo)
    request = CreateBookingRequest(
        tenant_id=tenant_id,
        service_id=service.id,
        resource_id=resource.id,
        customer_name="Ana",
        customer_contact="+34123456789",
        start=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc),
    )

    response = use_case.execute(request)

    assert response.booking_id is not None
    assert response.status == "pending"


def test_create_booking_fails_when_service_not_found() -> None:
    use_case = CreateBooking(
        InMemoryBookingRepository(),
        InMemoryServiceRepository(),
        InMemoryResourceRepository(),
    )
    request = CreateBookingRequest(
        tenant_id="tenant-a",
        service_id=Resource(name="unused").id,
        resource_id=Resource(name="unused2").id,
        customer_name="Ana",
        customer_contact="+34123456789",
        start=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc),
    )

    with pytest.raises(NotFoundError):
        use_case.execute(request)


def test_create_booking_fails_when_slot_is_taken() -> None:
    tenant_id = "tenant-a"
    service_repo = InMemoryServiceRepository()
    resource_repo = InMemoryResourceRepository()
    booking_repo = InMemoryBookingRepository()

    service = Service(name="Corte", duration_minutes=30, price=20.0)
    resource = Resource(name="Silla 1")
    service_repo.save(tenant_id, service)
    resource_repo.save(tenant_id, resource)

    use_case = CreateBooking(booking_repo, service_repo, resource_repo)

    first_request = CreateBookingRequest(
        tenant_id=tenant_id,
        service_id=service.id,
        resource_id=resource.id,
        customer_name="Ana",
        customer_contact="+34123456789",
        start=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc),
    )
    overlapping_request = CreateBookingRequest(
        tenant_id=tenant_id,
        service_id=service.id,
        resource_id=resource.id,
        customer_name="Luis",
        customer_contact="+34111222333",
        start=datetime(2026, 1, 1, 10, 15, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 10, 45, tzinfo=timezone.utc),
    )

    use_case.execute(first_request)

    with pytest.raises(ConflictError):
        use_case.execute(overlapping_request)
