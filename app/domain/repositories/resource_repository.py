from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities.resource import Resource


class ResourceRepository(ABC):
    @abstractmethod
    def get(self, tenant_id: str, resource_id: UUID) -> Optional[Resource]:
        pass

    @abstractmethod
    def save(self, tenant_id: str, resource: Resource) -> None:
        pass

    @abstractmethod
    def list(self, tenant_id: str) -> list[Resource]:
        pass
