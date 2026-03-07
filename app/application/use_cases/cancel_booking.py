from uuid import UUID
from dataclasses import dataclass

from app.domain.exceptions import NotFoundError
from app.domain.repositories.booking_repository import BookingRepository


@dataclass
class CancelBooking:
    booking_repository: BookingRepository

    def execute(self, tenant_id: str, booking_id: UUID) -> None:
        booking = self.booking_repository.get_by_id(booking_id)

        if booking is None:
            raise NotFoundError("Booking not found")
        if booking.tenant_id != tenant_id:
            raise NotFoundError("Booking not found")

        booking.cancel()

        self.booking_repository.save(booking)
