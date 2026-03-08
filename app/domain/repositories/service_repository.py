from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities.service import Service


class ServiceRepository(ABC):
    @abstractmethod
    def get(self, tenant_id: str, service_id: UUID) -> Optional[Service]:
        pass

    @abstractmethod
    def save(self, tenant_id: str, service: Service) -> None:
        pass

    @abstractmethod
    def list(self, tenant_id: str) -> list[Service]:
        pass
