from typing import Iterable

from app.domain.entities.booking import Booking
from app.domain.exceptions import ConflictError
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.value_objects.booking_status import BookingStatus


class AvailabilityPolicy:
    @staticmethod
    def ensure_available(
        existing_bookings: Iterable[Booking],
        requested_slot: TimeSlot,
    ) -> None:

        for booking in existing_bookings:
            if booking.status in (BookingStatus.CANCELLED, BookingStatus.COMPLETED):
                continue

            if booking.time_slot.overlaps(requested_slot):
                raise ConflictError("Time slot not available")
