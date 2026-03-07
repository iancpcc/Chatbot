import os
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.domain.entities.resource import Resource
from app.domain.entities.service import Service
from app.infrastructure.persistence.sqlalchemy_database import engine
from app.infrastructure.persistence.sqlalchemy_models import Base, ResourceModel, ServiceModel
from app.infrastructure.persistence.sqlalchemy_resource_repository import (
    SqlAlchemyResourceRepository,
)
from app.infrastructure.persistence.sqlalchemy_service_repository import (
    SqlAlchemyServiceRepository,
)


DEMO_TENANT_ID = "demo-salon"
DEMO_SERVICE_ID = UUID("11111111-1111-1111-1111-111111111111")
DEMO_RESOURCE_ID = UUID("22222222-2222-2222-2222-222222222222")


def init_schema() -> None:
    # In docker-compose, Postgres may not be ready when the API starts.
    # Retry for a short, configurable window to avoid crashing on startup.
    max_wait_seconds = float(os.getenv("DB_INIT_MAX_WAIT_SECONDS", "10"))
    deadline = time.time() + max_wait_seconds
    attempt = 0

    while True:
        attempt += 1
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            if time.time() >= deadline:
                raise
            sleep_seconds = min(0.25 * (2 ** (attempt - 1)), 2.0)
            time.sleep(sleep_seconds)


def seed_demo_catalog() -> None:
    service_repo = SqlAlchemyServiceRepository()
    resource_repo = SqlAlchemyResourceRepository()

    with engine.connect() as conn:
        service_exists = conn.execute(
            select(ServiceModel.id).where(
                ServiceModel.tenant_id == DEMO_TENANT_ID,
                ServiceModel.id == str(DEMO_SERVICE_ID),
            )
        ).first()
        resource_exists = conn.execute(
            select(ResourceModel.id).where(
                ResourceModel.tenant_id == DEMO_TENANT_ID,
                ResourceModel.id == str(DEMO_RESOURCE_ID),
            )
        ).first()

    if not service_exists:
        service_repo.save(
            DEMO_TENANT_ID,
            Service(
                id=DEMO_SERVICE_ID,
                name="Corte de cabello",
                duration_minutes=30,
                price=20.0,
            ),
        )

    if not resource_exists:
        resource_repo.save(
            DEMO_TENANT_ID,
            Resource(
                id=DEMO_RESOURCE_ID,
                name="Silla 1",
            ),
        )
