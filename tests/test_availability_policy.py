from datetime import datetime, timezone

import pytest

from app.domain.entities.booking import Booking
from app.domain.entities.customer import Customer
from app.domain.entities.resource import Resource
from app.domain.entities.service import Service
from app.domain.exceptions import ConflictError
from app.domain.services.availability_policy import AvailabilityPolicy
from app.domain.value_objects.time_slot import TimeSlot


def test_availability_policy_raises_conflict_on_overlap() -> None:
    service = Service(name="Corte", duration_minutes=30, price=20.0)
    resource = Resource(name="Silla 1")
    customer = Customer(full_name="Ana", contact="+34123456789")

    existing = Booking(
        tenant_id="tenant-a",
        service=service,
        resource=resource,
        customer=customer,
        time_slot=TimeSlot(
            start=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            end=datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
        ),
    )
    requested = TimeSlot(
        start=datetime(2026, 1, 1, 10, 30, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 11, 30, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ConflictError):
        AvailabilityPolicy.ensure_available([existing], requested)
