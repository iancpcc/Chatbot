from abc import ABC, abstractmethod
from datetime import datetime
from typing import List
from uuid import UUID
from typing import Optional
from app.domain.entities.booking import Booking


class BookingRepository(ABC):
    @abstractmethod
    def save(self, booking: Booking) -> None:
        pass

    @abstractmethod
    def get_by_id(self, booking_id: UUID) -> Optional[Booking]:
        pass

    @abstractmethod
    def get_by_resource(self, tenant_id: str, resource_id: UUID) -> List[Booking]:
        pass

    @abstractmethod
    def list(
        self,
        tenant_id: str,
        resource_id: UUID | None = None,
        start_from: datetime | None = None,
        end_to: datetime | None = None,
    ) -> List[Booking]:
        pass
