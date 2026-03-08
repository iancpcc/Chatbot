from uuid import UUID

from sqlalchemy import select

from app.domain.entities.resource import Resource
from app.domain.repositories.resource_repository import ResourceRepository
from app.infrastructure.persistence.sqlalchemy_database import SessionLocal
from app.infrastructure.persistence.sqlalchemy_models import ResourceModel


class SqlAlchemyResourceRepository(ResourceRepository):
    def get(self, tenant_id: str, resource_id: UUID) -> Resource | None:
        with SessionLocal() as session:
            stmt = select(ResourceModel).where(
                ResourceModel.tenant_id == tenant_id,
                ResourceModel.id == str(resource_id),
            )
            row = session.execute(stmt).scalar_one_or_none()
            if row is None:
                return None
            return Resource(
                id=UUID(row.id),
                name=row.name,
            )

    def save(self, tenant_id: str, resource: Resource) -> None:
        with SessionLocal() as session:
            row = session.get(ResourceModel, (str(resource.id), tenant_id))
            if row is None:
                row = ResourceModel(
                    id=str(resource.id),
                    tenant_id=tenant_id,
                    name=resource.name,
                )
                session.add(row)
            else:
                row.name = resource.name
            session.commit()

    def list(self, tenant_id: str) -> list[Resource]:
        with SessionLocal() as session:
            stmt = (
                select(ResourceModel)
                .where(ResourceModel.tenant_id == tenant_id)
                .order_by(ResourceModel.name.asc(), ResourceModel.id.asc())
            )
            rows = session.execute(stmt).scalars().all()
            return [Resource(id=UUID(row.id), name=row.name) for row in rows]
