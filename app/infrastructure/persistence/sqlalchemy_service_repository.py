from uuid import UUID

from sqlalchemy import select

from app.domain.entities.service import Service
from app.domain.repositories.service_repository import ServiceRepository
from app.infrastructure.persistence.sqlalchemy_database import SessionLocal
from app.infrastructure.persistence.sqlalchemy_models import ServiceModel


class SqlAlchemyServiceRepository(ServiceRepository):
    def get(self, tenant_id: str, service_id: UUID) -> Service | None:
        with SessionLocal() as session:
            stmt = select(ServiceModel).where(
                ServiceModel.tenant_id == tenant_id,
                ServiceModel.id == str(service_id),
            )
            row = session.execute(stmt).scalar_one_or_none()
            if row is None:
                return None
            return Service(
                id=UUID(row.id),
                name=row.name,
                duration_minutes=row.duration_minutes,
                price=row.price,
            )

    def save(self, tenant_id: str, service: Service) -> None:
        with SessionLocal() as session:
            row = session.get(ServiceModel, (str(service.id), tenant_id))
            if row is None:
                row = ServiceModel(
                    id=str(service.id),
                    tenant_id=tenant_id,
                    name=service.name,
                    duration_minutes=service.duration_minutes,
                    price=service.price,
                )
                session.add(row)
            else:
                row.name = service.name
                row.duration_minutes = service.duration_minutes
                row.price = service.price
            session.commit()
