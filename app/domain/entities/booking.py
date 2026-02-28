from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.entities.customer import Customer
from app.domain.entities.resource import Resource
from app.domain.entities.service import Service
from app.domain.value_objects.booking_status import BookingStatus
from app.domain.value_objects.time_slot import TimeSlot


@dataclass
class Booking:
    tenant_id: str
    service: Service
    resource: Resource
    customer: Customer
    time_slot: TimeSlot
    id: UUID = field(default_factory=uuid4)
    status: BookingStatus = BookingStatus.PENDING

    def confirm(self) -> None:
        if self.status == BookingStatus.CANCELLED:
            raise ValueError("Cannot confirm an cancelled booking")
        self.status = BookingStatus.CONFIRMED

    def cancel(self) -> None:
        if self.status == BookingStatus.CANCELLED:
            raise ValueError("Booking already cancelled")

        if self.status == BookingStatus.COMPLETED:
            raise ValueError("Completed booking cannot be cancelled")

        self.status = BookingStatus.CANCELLED

    def complete(self) -> None:
        if self.status != BookingStatus.CONFIRMED:
            raise ValueError("Only confirmed bookings can be completed")

        self.status = BookingStatus.COMPLETED

    def is_available(self, existing_bookings: list["Booking"]) -> bool:
        if self.status == BookingStatus.CANCELLED:
            return False

        for existing in existing_bookings:
            if existing.id == self.id:
                continue

            if existing.status == BookingStatus.CANCELLED:
                continue

            if existing.resource == self.resource and existing.time_slot.overlaps(
                self.time_slot
            ):
                return False

        return True

    def is_overlapping(self, other: "Booking") -> bool:
        return self.resource == other.resource and self.time_slot.overlaps(
            other.time_slot
        )

    def is_past(self) -> bool:
        return self.time_slot.end < datetime.now(timezone.utc)

    def is_future(self) -> bool:
        return self.time_slot.start > datetime.now(timezone.utc)

    def is_ongoing(self) -> bool:
        return self.time_slot.start <= datetime.now(timezone.utc) <= self.time_slot.end

    def is_cancelled(self) -> bool:
        return self.status == BookingStatus.CANCELLED

    def is_confirmed(self) -> bool:
        return self.status == BookingStatus.CONFIRMED

    def is_pending(self) -> bool:
        return self.status == BookingStatus.PENDING

    def is_completed(self) -> bool:
        return (
            self.status == BookingStatus.CONFIRMED
            and self.time_slot.end < datetime.now(timezone.utc)
        )

    def is_reschedulable(self) -> bool:
        return (
            self.status == BookingStatus.CONFIRMED
            and self.time_slot.start > datetime.now(timezone.utc)
        )
