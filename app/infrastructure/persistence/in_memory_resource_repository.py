from typing import Optional
from uuid import UUID

from app.domain.entities.resource import Resource
from app.domain.repositories.resource_repository import ResourceRepository


class InMemoryResourceRepository(ResourceRepository):
    def __init__(self):
        self._storage: dict[tuple[str, UUID], Resource] = {}

    def get(self, tenant_id: str, resource_id: UUID) -> Optional[Resource]:
        return self._storage.get((tenant_id, resource_id))

    def save(self, tenant_id: str, resource: Resource) -> None:
        self._storage[(tenant_id, resource.id)] = resource
