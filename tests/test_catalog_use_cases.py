from app.application.use_cases.list_resources import ListResources, ListResourcesRequest
from app.application.use_cases.list_services import ListServices, ListServicesRequest
from app.domain.entities.resource import Resource
from app.domain.entities.service import Service
from app.infrastructure.persistence.in_memory_resource_repository import (
    InMemoryResourceRepository,
)
from app.infrastructure.persistence.in_memory_service_repository import (
    InMemoryServiceRepository,
)


def test_list_services_is_tenant_scoped_and_sorted() -> None:
    repository = InMemoryServiceRepository()
    tenant_a = "tenant-catalog-a"
    tenant_b = "tenant-catalog-b"

    repository.save(
        tenant_a,
        Service(name="B corte", duration_minutes=30, price=20.0),
    )
    repository.save(
        tenant_a,
        Service(name="A corte", duration_minutes=45, price=25.0),
    )
    repository.save(
        tenant_b,
        Service(name="Z otro", duration_minutes=10, price=1.0),
    )

    result_a = ListServices(repository).execute(ListServicesRequest(tenant_id=tenant_a))
    result_b = ListServices(repository).execute(ListServicesRequest(tenant_id=tenant_b))

    assert [item.name for item in result_a] == ["A corte", "B corte"]
    assert all(item.tenant_id == tenant_a for item in result_a)
    assert [item.name for item in result_b] == ["Z otro"]
    assert all(item.tenant_id == tenant_b for item in result_b)


def test_list_resources_is_tenant_scoped_and_sorted() -> None:
    repository = InMemoryResourceRepository()
    tenant_a = "tenant-catalog-a"
    tenant_b = "tenant-catalog-b"

    repository.save(tenant_a, Resource(name="Silla 2"))
    repository.save(tenant_a, Resource(name="Silla 1"))
    repository.save(tenant_b, Resource(name="Cabina Z"))

    result_a = ListResources(repository).execute(
        ListResourcesRequest(tenant_id=tenant_a)
    )
    result_b = ListResources(repository).execute(
        ListResourcesRequest(tenant_id=tenant_b)
    )

    assert [item.name for item in result_a] == ["Silla 1", "Silla 2"]
    assert all(item.tenant_id == tenant_a for item in result_a)
    assert [item.name for item in result_b] == ["Cabina Z"]
    assert all(item.tenant_id == tenant_b for item in result_b)
