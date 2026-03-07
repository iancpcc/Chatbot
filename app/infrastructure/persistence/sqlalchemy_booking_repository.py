from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.domain.entities.booking import Booking
from app.domain.entities.customer import Customer
from app.domain.entities.resource import Resource
from app.domain.entities.service import Service
from app.domain.repositories.booking_repository import BookingRepository
from app.domain.value_objects.booking_status import BookingStatus
from app.domain.value_objects.time_slot import TimeSlot
from app.infrastructure.persistence.sqlalchemy_database import SessionLocal
from app.infrastructure.persistence.sqlalchemy_models import (
    BookingModel,
    ResourceModel,
    ServiceModel,
)


class SqlAlchemyBookingRepository(BookingRepository):
    def save(self, booking: Booking) -> None:
        with SessionLocal() as session:
            row = session.get(BookingModel, str(booking.id))
            if row is None:
                row = BookingModel(
                    id=str(booking.id),
                    tenant_id=booking.tenant_id,
                    service_id=str(booking.service.id),
                    resource_id=str(booking.resource.id),
                    customer_name=booking.customer.full_name,
                    customer_contact=booking.customer.contact,
                    start_at=booking.time_slot.start,
                    end_at=booking.time_slot.end,
                    status=booking.status.value,
                )
                session.add(row)
            else:
                row.service_id = str(booking.service.id)
                row.resource_id = str(booking.resource.id)
                row.customer_name = booking.customer.full_name
                row.customer_contact = booking.customer.contact
                row.start_at = booking.time_slot.start
                row.end_at = booking.time_slot.end
                row.status = booking.status.value
            session.commit()

    def get_by_id(self, booking_id: UUID) -> Booking | None:
        with SessionLocal() as session:
            stmt = select(BookingModel).where(BookingModel.id == str(booking_id))
            row = session.execute(stmt).scalar_one_or_none()
            if row is None:
                return None
            return self._to_entity(session, row)

    def get_by_resource(self, tenant_id: str, resource_id: UUID) -> list[Booking]:
        with SessionLocal() as session:
            stmt = select(BookingModel).where(
                BookingModel.tenant_id == tenant_id,
                BookingModel.resource_id == str(resource_id),
            )
            rows = session.execute(stmt).scalars().all()
            return [self._to_entity(session, row) for row in rows]

    def list(
        self,
        tenant_id: str,
        resource_id: UUID | None = None,
        start_from: datetime | None = None,
        end_to: datetime | None = None,
    ) -> list[Booking]:
        with SessionLocal() as session:
            stmt = select(BookingModel).where(BookingModel.tenant_id == tenant_id)
            if resource_id is not None:
                stmt = stmt.where(BookingModel.resource_id == str(resource_id))
            if start_from is not None:
                stmt = stmt.where(BookingModel.start_at >= start_from)
            if end_to is not None:
                stmt = stmt.where(BookingModel.end_at <= end_to)
            stmt = stmt.order_by(BookingModel.start_at.asc())
            rows = session.execute(stmt).scalars().all()
            return [self._to_entity(session, row) for row in rows]

    def _to_entity(self, session, row: BookingModel) -> Booking:
        service_row = session.execute(
            select(ServiceModel).where(
                ServiceModel.tenant_id == row.tenant_id,
                ServiceModel.id == row.service_id,
            )
        ).scalar_one()
        resource_row = session.execute(
            select(ResourceModel).where(
                ResourceModel.tenant_id == row.tenant_id,
                ResourceModel.id == row.resource_id,
            )
        ).scalar_one()

        return Booking(
            id=UUID(row.id),
            tenant_id=row.tenant_id,
            service=Service(
                id=UUID(service_row.id),
                name=service_row.name,
                duration_minutes=service_row.duration_minutes,
                price=service_row.price,
            ),
            resource=Resource(
                id=UUID(resource_row.id),
                name=resource_row.name,
            ),
            customer=Customer(
                full_name=row.customer_name,
                contact=row.customer_contact,
            ),
            time_slot=TimeSlot(
                start=self._ensure_timezone(row.start_at),
                end=self._ensure_timezone(row.end_at),
            ),
            status=BookingStatus(row.status),
        )

    @staticmethod
    def _ensure_timezone(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
