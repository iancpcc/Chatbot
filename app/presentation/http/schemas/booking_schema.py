from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class CreateBookingRequest(BaseModel):
    tenant_id: str
    service_id: UUID
    resource_id: UUID
    customer_name: str
    customer_contact: str
    start: datetime
    end: datetime


class CreateBookingResponse(BaseModel):
    booking_id: UUID
    status: str


class BookingItemResponse(BaseModel):
    booking_id: UUID
    tenant_id: str
    service_id: UUID
    resource_id: UUID
    customer_name: str
    customer_contact: str
    start: datetime
    end: datetime
    status: str
