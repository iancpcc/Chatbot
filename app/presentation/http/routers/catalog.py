from fastapi import APIRouter, Depends

from app.application.use_cases.create_resource import (
    CreateResource,
    CreateResourceRequest as CreateResourceUseCaseRequest,
)
from app.application.use_cases.create_service import (
    CreateService,
    CreateServiceRequest as CreateServiceUseCaseRequest,
)
from app.presentation.http.dependencies import (
    get_create_resource_use_case,
    get_create_service_use_case,
)
from app.presentation.http.schemas.catalog_schema import (
    CreateResourceRequest,
    CreateResourceResponse,
    CreateServiceRequest,
    CreateServiceResponse,
)

router = APIRouter(prefix="", tags=["Catalog"])


@router.post("/services", response_model=CreateServiceResponse)
def create_service(
    request: CreateServiceRequest,
    use_case: CreateService = Depends(get_create_service_use_case),
):
    result = use_case.execute(
        CreateServiceUseCaseRequest(
            tenant_id=request.tenant_id,
            name=request.name,
            duration_minutes=request.duration_minutes,
            price=request.price,
        )
    )
    return CreateServiceResponse(
        service_id=result.service_id,
        name=result.name,
        duration_minutes=result.duration_minutes,
        price=result.price,
    )


@router.post("/resources", response_model=CreateResourceResponse)
def create_resource(
    request: CreateResourceRequest,
    use_case: CreateResource = Depends(get_create_resource_use_case),
):
    result = use_case.execute(
        CreateResourceUseCaseRequest(
            tenant_id=request.tenant_id,
            name=request.name,
        )
    )
    return CreateResourceResponse(
        resource_id=result.resource_id,
        name=result.name,
    )
