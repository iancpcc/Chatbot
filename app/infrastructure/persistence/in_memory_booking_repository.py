from datetime import datetime
from typing import List
from uuid import UUID
from typing import Optional

from app.domain.entities.booking import Booking
from app.domain.repositories.booking_repository import BookingRepository


class InMemoryBookingRepository(BookingRepository):
    def __init__(self):
        self._storage: dict[UUID, Booking] = {}

    def get_by_id(self, booking_id: UUID) -> Optional[Booking]:
        return self._storage.get(booking_id)

    def save(self, booking: Booking) -> None:
        self._storage[booking.id] = booking

    def get_by_resource(self, tenant_id: str, resource_id: UUID) -> List[Booking]:
        return [
            b
            for b in self._storage.values()
            if b.tenant_id == tenant_id
            and b.resource.id == resource_id
        ]

    def list(
        self,
        tenant_id: str,
        resource_id: UUID | None = None,
        start_from: datetime | None = None,
        end_to: datetime | None = None,
    ) -> List[Booking]:
        results = [b for b in self._storage.values() if b.tenant_id == tenant_id]

        if resource_id is not None:
            results = [b for b in results if b.resource.id == resource_id]
        if start_from is not None:
            results = [b for b in results if b.time_slot.start >= start_from]
        if end_to is not None:
            results = [b for b in results if b.time_slot.end <= end_to]

        return sorted(results, key=lambda booking: booking.time_slot.start)
