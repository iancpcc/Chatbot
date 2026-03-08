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


class ServiceItemResponse(BaseModel):
    service_id: UUID
    tenant_id: str
    name: str
    duration_minutes: int
    price: float


class ResourceItemResponse(BaseModel):
    resource_id: UUID
    tenant_id: str
    name: str
