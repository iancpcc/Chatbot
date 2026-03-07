from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.repositories.booking_repository import BookingRepository


@dataclass
class ListBookingsRequest:
    tenant_id: str
    resource_id: UUID | None = None
    start_from: datetime | None = None
    end_to: datetime | None = None


@dataclass
class BookingItem:
    booking_id: UUID
    tenant_id: str
    service_id: UUID
    resource_id: UUID
    customer_name: str
    customer_contact: str
    start: datetime
    end: datetime
    status: str


class ListBookings:
    def __init__(self, booking_repository: BookingRepository):
        self.booking_repository = booking_repository

    def execute(self, request: ListBookingsRequest) -> list[BookingItem]:
        bookings = self.booking_repository.list(
            tenant_id=request.tenant_id,
            resource_id=request.resource_id,
            start_from=request.start_from,
            end_to=request.end_to,
        )
        return [
            BookingItem(
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
            for booking in bookings
        ]
