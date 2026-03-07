from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.resource import Resource
from app.domain.exceptions import ValidationError
from app.domain.repositories.resource_repository import ResourceRepository


@dataclass
class CreateResourceRequest:
    tenant_id: str
    name: str


@dataclass
class CreateResourceResponse:
    resource_id: UUID
    name: str


class CreateResource:
    def __init__(self, resource_repository: ResourceRepository):
        self.resource_repository = resource_repository

    def execute(self, request: CreateResourceRequest) -> CreateResourceResponse:
        if not request.name.strip():
            raise ValidationError("name must not be empty")

        resource = Resource(name=request.name.strip())
        self.resource_repository.save(request.tenant_id, resource)

        return CreateResourceResponse(resource_id=resource.id, name=resource.name)
