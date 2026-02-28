from typing import Optional
from uuid import UUID

from app.domain.entities.service import Service
from app.domain.repositories.service_repository import ServiceRepository


class InMemoryServiceRepository(ServiceRepository):
    def __init__(self):
        self._storage: dict[tuple[str, UUID], Service] = {}

    def get(self, tenant_id: str, service_id: UUID) -> Optional[Service]:
        return self._storage.get((tenant_id, service_id))

    def save(self, tenant_id: str, service: Service) -> None:
        self._storage[(tenant_id, service.id)] = service
