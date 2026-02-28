from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class CreateBookingRequest:
    tenant_id: str
    service_id: UUID
    resource_id: UUID
    customer_name: str
    customer_contact: str
    start: datetime
    end: datetime


@dataclass
class CreateBookingResponse:
    booking_id: UUID
    status: str
