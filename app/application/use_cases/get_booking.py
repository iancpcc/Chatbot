from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.exceptions import NotFoundError
from app.domain.repositories.booking_repository import BookingRepository


@dataclass
class BookingDetails:
    booking_id: UUID
    tenant_id: str
    service_id: UUID
    resource_id: UUID
    customer_name: str
    customer_contact: str
    start: datetime
    end: datetime
    status: str


class GetBooking:
    def __init__(self, booking_repository: BookingRepository):
        self.booking_repository = booking_repository

    def execute(self, tenant_id: str, booking_id: UUID) -> BookingDetails:
        booking = self.booking_repository.get_by_id(booking_id)
        if booking is None or booking.tenant_id != tenant_id:
            raise NotFoundError("Booking not found")

        return BookingDetails(
            booking_id=booking.id,
            tenant_id=booking.tenant_id,
            service_id=booking.service.id,
            resource_id=booking.resource.id,
            customer_name=booking.customer.full_name,
            customer_contact=booking.customer.contact,
            start=booking.time_slot.start,
            end=booking.time_slot.end,
            status=booking.status.value,
        )
