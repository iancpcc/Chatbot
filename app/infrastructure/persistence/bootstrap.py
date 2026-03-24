import os
import time
from typing import Any
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.domain.entities.resource import Resource
from app.domain.entities.service import Service
from app.infrastructure.persistence.sqlalchemy_database import engine
from app.infrastructure.persistence.sqlalchemy_models import ResourceModel, ServiceModel
from app.infrastructure.persistence.sqlalchemy_resource_repository import (
    SqlAlchemyResourceRepository,
)
from app.infrastructure.persistence.sqlalchemy_service_repository import (
    SqlAlchemyServiceRepository,
)


from uuid import uuid4

NAILS_TENANT_ID = "nails-studio-ec"


# ---------- RESOURCES ----------
def build_resources():
    return [
        {
            "id": uuid4(),
            "name": "Local 1",
        }
    ]


# ---------- SERVICES (USD - Ecuador market) ----------
SERVICES: list[dict[str, Any]] = [
    # Uñas
    {"name": "Manicura básica", "duration": 30, "price": 10.0},
    {"name": "Manicura semipermanente", "duration": 45, "price": 18.0},
    {"name": "Uñas acrílicas completas", "duration": 90, "price": 35.0},
    {"name": "Relleno uñas acrílicas", "duration": 60, "price": 20.0},
    {"name": "Pedicura completa", "duration": 60, "price": 20.0},
    # Facial
    {"name": "Limpieza facial básica", "duration": 60, "price": 25.0},
    {"name": "Limpieza facial profunda", "duration": 90, "price": 40.0},
    {"name": "Tratamiento antiacné", "duration": 60, "price": 35.0},
    {"name": "Tratamiento hidratante facial", "duration": 60, "price": 30.0},
    # Masajes
    {"name": "Masaje relajante", "duration": 60, "price": 30.0},
    {"name": "Masaje descontracturante", "duration": 45, "price": 25.0},
    {"name": "Masaje corporal completo", "duration": 90, "price": 45.0},
    # Depilación
    {"name": "Depilación cejas", "duration": 15, "price": 5.0},
    {"name": "Depilación labio superior", "duration": 10, "price": 4.0},
    {"name": "Depilación piernas completas", "duration": 45, "price": 18.0},
    {"name": "Depilación ingles", "duration": 20, "price": 10.0},
]


def apply_migrations() -> None:
    # In docker-compose, Postgres may not be ready when the API starts.
    # Retry for a short, configurable window to avoid crashing on startup.
    max_wait_seconds = float(os.getenv("DB_INIT_MAX_WAIT_SECONDS", "10"))
    deadline = time.time() + max_wait_seconds
    attempt = 0

    while True:
        attempt += 1
        try:
            _wait_until_db_ready()
            command.upgrade(_alembic_config(), "head")
            return
        except OperationalError:
            if time.time() >= deadline:
                raise
            sleep_seconds = min(0.25 * (2 ** (attempt - 1)), 2.0)
            time.sleep(sleep_seconds)


def _wait_until_db_ready() -> None:
    with engine.connect():
        return


def _alembic_config() -> Config:
    project_root = Path(__file__).resolve().parents[3]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    return config


def seed_nails_ec_catalog() -> None:
    service_repo = SqlAlchemyServiceRepository()
    resource_repo = SqlAlchemyResourceRepository()

    resources = build_resources()

    with engine.connect() as conn:
        # ---- RESOURCES (UUID dinámico) ----
        for r in resources:
            exists = conn.execute(
                select(ResourceModel.id).where(
                    ResourceModel.tenant_id == NAILS_TENANT_ID,
                    ResourceModel.name == r["name"],  # clave natural
                )
            ).first()

            if not exists:
                resource_repo.save(
                    NAILS_TENANT_ID,
                    Resource(
                        id=r["id"],
                        name=r["name"],
                    ),
                )

        # ---- SERVICES ----
        for s in SERVICES:
            exists = conn.execute(
                select(ServiceModel.id).where(
                    ServiceModel.tenant_id == NAILS_TENANT_ID,
                    ServiceModel.name == s["name"],
                )
            ).first()

            if not exists:
                service_repo.save(
                    NAILS_TENANT_ID,
                    Service(
                        id=uuid4(),  # UID autogenerado
                        name=s["name"],
                        duration_minutes=s["duration"],
                        price=s["price"],
                    ),
                )
