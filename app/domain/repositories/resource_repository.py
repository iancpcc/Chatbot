from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities.resource import Resource


class ResourceRepository(ABC):
    @abstractmethod
    def get(self, tenant_id: str, resource_id: UUID) -> Optional[Resource]:
        pass
