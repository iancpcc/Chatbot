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

    def list(self, tenant_id: str) -> list[Resource]:
        resources = [r for (t_id, _), r in self._storage.items() if t_id == tenant_id]
        return sorted(resources, key=lambda r: (r.name.lower(), str(r.id)))
