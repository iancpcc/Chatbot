from uuid import UUID

from pydantic import BaseModel


class CreateServiceRequest(BaseModel):
    tenant_id: str
    name: str
    duration_minutes: int
    price: float


class CreateServiceResponse(BaseModel):
    service_id: UUID
    name: str
    duration_minutes: int
    price: float


class CreateResourceRequest(BaseModel):
    tenant_id: str
    name: str


class CreateResourceResponse(BaseModel):
    resource_id: UUID
    name: str
