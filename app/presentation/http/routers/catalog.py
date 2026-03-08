from fastapi import APIRouter, Depends, Query

from app.application.use_cases.create_resource import (
    CreateResource,
    CreateResourceRequest as CreateResourceUseCaseRequest,
)
from app.application.use_cases.create_service import (
    CreateService,
    CreateServiceRequest as CreateServiceUseCaseRequest,
)
from app.application.use_cases.list_resources import (
    ListResources,
    ListResourcesRequest,
)
from app.application.use_cases.list_services import ListServices, ListServicesRequest
from app.presentation.http.dependencies import (
    get_create_resource_use_case,
    get_create_service_use_case,
    get_list_resources_use_case,
    get_list_services_use_case,
)
from app.presentation.http.schemas.catalog_schema import (
    CreateResourceRequest,
    CreateResourceResponse,
    CreateServiceRequest,
    CreateServiceResponse,
    ResourceItemResponse,
    ServiceItemResponse,
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

@router.get("/services", response_model=list[ServiceItemResponse])
def list_services(
    tenant_id: str = Query(...),
    use_case: ListServices = Depends(get_list_services_use_case),
):
    items = use_case.execute(ListServicesRequest(tenant_id=tenant_id))
    return [
        ServiceItemResponse(
            service_id=i.service_id,
            tenant_id=i.tenant_id,
            name=i.name,
            duration_minutes=i.duration_minutes,
            price=i.price,
        )
        for i in items
    ]


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


@router.get("/resources", response_model=list[ResourceItemResponse])
def list_resources(
    tenant_id: str = Query(...),
    use_case: ListResources = Depends(get_list_resources_use_case),
):
    items = use_case.execute(ListResourcesRequest(tenant_id=tenant_id))
    return [
        ResourceItemResponse(
            resource_id=i.resource_id,
            tenant_id=i.tenant_id,
            name=i.name,
        )
        for i in items
    ]
