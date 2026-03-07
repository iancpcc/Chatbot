from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.service import Service
from app.domain.exceptions import ValidationError
from app.domain.repositories.service_repository import ServiceRepository


@dataclass
class CreateServiceRequest:
    tenant_id: str
    name: str
    duration_minutes: int
    price: float


@dataclass
class CreateServiceResponse:
    service_id: UUID
    name: str
    duration_minutes: int
    price: float


class CreateService:
    def __init__(self, service_repository: ServiceRepository):
        self.service_repository = service_repository

    def execute(self, request: CreateServiceRequest) -> CreateServiceResponse:
        if request.duration_minutes <= 0:
            raise ValidationError("duration_minutes must be greater than 0")
        if request.price < 0:
            raise ValidationError("price must be greater or equal to 0")

        service = Service(
            name=request.name,
            duration_minutes=request.duration_minutes,
            price=request.price,
        )
        self.service_repository.save(request.tenant_id, service)

        return CreateServiceResponse(
            service_id=service.id,
            name=service.name,
            duration_minutes=service.duration_minutes,
            price=service.price,
        )
