from dataclasses import dataclass
from uuid import UUID

from app.domain.repositories.service_repository import ServiceRepository


@dataclass
class ListServicesRequest:
    tenant_id: str


@dataclass
class ServiceItem:
    service_id: UUID
    tenant_id: str
    name: str
    duration_minutes: int
    price: float


class ListServices:
    def __init__(self, service_repository: ServiceRepository):
        self.service_repository = service_repository

    def execute(self, request: ListServicesRequest) -> list[ServiceItem]:
        services = self.service_repository.list(request.tenant_id)
        return [
            ServiceItem(
                service_id=s.id,
                tenant_id=request.tenant_id,
                name=s.name,
                duration_minutes=s.duration_minutes,
                price=s.price,
            )
            for s in services
        ]

