from dataclasses import dataclass
from uuid import UUID

from app.domain.repositories.resource_repository import ResourceRepository


@dataclass
class ListResourcesRequest:
    tenant_id: str


@dataclass
class ResourceItem:
    resource_id: UUID
    tenant_id: str
    name: str


class ListResources:
    def __init__(self, resource_repository: ResourceRepository):
        self.resource_repository = resource_repository

    def execute(self, request: ListResourcesRequest) -> list[ResourceItem]:
        resources = self.resource_repository.list(request.tenant_id)
        return [
            ResourceItem(
                resource_id=r.id,
                tenant_id=request.tenant_id,
                name=r.name,
            )
            for r in resources
        ]

