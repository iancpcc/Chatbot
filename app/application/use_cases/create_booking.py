from app.domain.repositories.booking_repository import BookingRepository
from app.domain.repositories.service_repository import ServiceRepository
from app.domain.repositories.resource_repository import ResourceRepository
from app.application.dto.create_booking_dto import (
    CreateBookingRequest,
    CreateBookingResponse,
)
from app.domain.entities.resource import Resource
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities.booking import Booking
from app.domain.entities.customer import Customer
from app.domain.value_objects.time_slot import TimeSlot

from app.domain.services.availability_policy import AvailabilityPolicy


class CreateBooking:
    def __init__(
        self,
        booking_repository: BookingRepository,
        service_repository: ServiceRepository,
        resource_repository: ResourceRepository,
    ):
        self.booking_repository = booking_repository
        self.service_repository = service_repository
        self.resource_repository = resource_repository

    def execute(self, request: CreateBookingRequest) -> CreateBookingResponse:
        service = self.service_repository.get(request.tenant_id, request.service_id)
        if not service:
            raise NotFoundError("Service not found")

        customer = Customer(
            full_name=request.customer_name,
            contact=request.customer_contact,
        )

        time_slot = TimeSlot(start=request.start, end=request.end)
        requested_minutes = int((time_slot.end - time_slot.start).total_seconds() / 60)
        if requested_minutes != service.duration_minutes:
            raise ValidationError(
                "Requested slot duration must match service duration_minutes"
            )

        resource = self._resolve_resource(request=request, requested_slot=time_slot)

        booking = Booking(
            tenant_id=request.tenant_id,
            service=service,
            resource=resource,
            customer=customer,
            time_slot=time_slot,
        )

        self.booking_repository.save(booking)

        return CreateBookingResponse(
            booking_id=booking.id,
            status=booking.status.value,
        )

    def _resolve_resource(
        self,
        *,
        request: CreateBookingRequest,
        requested_slot: TimeSlot,
    ) -> Resource:
        if request.resource_id is not None:
            selected = self.resource_repository.get(request.tenant_id, request.resource_id)
            if not selected:
                raise NotFoundError("Resource not found")
            self._ensure_slot_available_for_resource(
                tenant_id=request.tenant_id,
                resource=selected,
                requested_slot=requested_slot,
            )
            return selected

        resources = self.resource_repository.list(request.tenant_id)
        if not resources:
            raise NotFoundError("No resources available for tenant")

        for resource in resources:
            if self._is_resource_available(
                tenant_id=request.tenant_id,
                resource=resource,
                requested_slot=requested_slot,
            ):
                return resource

        raise ConflictError("Time slot not available")

    def _is_resource_available(
        self,
        *,
        tenant_id: str,
        resource: Resource,
        requested_slot: TimeSlot,
    ) -> bool:
        try:
            self._ensure_slot_available_for_resource(
                tenant_id=tenant_id,
                resource=resource,
                requested_slot=requested_slot,
            )
            return True
        except ConflictError:
            return False

    def _ensure_slot_available_for_resource(
        self,
        *,
        tenant_id: str,
        resource: Resource,
        requested_slot: TimeSlot,
    ) -> None:
        existing_bookings = self.booking_repository.get_by_resource(
            tenant_id=tenant_id,
            resource_id=resource.id,
        )
        AvailabilityPolicy.ensure_available(
            existing_bookings=existing_bookings,
            requested_slot=requested_slot,
        )
