from fastapi.testclient import TestClient

from app.main import app
from app.presentation.http.dependencies import reset_state


def test_http_list_services_and_resources_is_tenant_scoped_and_sorted() -> None:
    reset_state()
    client = TestClient(app)

    tenant_a = "tenant-catalog-a"
    tenant_b = "tenant-catalog-b"

    # Services (intentionally out of order)
    client.post(
        "/v1/services",
        json={
            "tenant_id": tenant_a,
            "name": "B corte",
            "duration_minutes": 30,
            "price": 20.0,
        },
    )
    client.post(
        "/v1/services",
        json={
            "tenant_id": tenant_a,
            "name": "A corte",
            "duration_minutes": 45,
            "price": 25.0,
        },
    )
    client.post(
        "/v1/services",
        json={
            "tenant_id": tenant_b,
            "name": "Z otro",
            "duration_minutes": 10,
            "price": 1.0,
        },
    )

    services_a = client.get("/v1/services", params={"tenant_id": tenant_a})
    assert services_a.status_code == 200
    data_a = services_a.json()
    assert [s["name"] for s in data_a] == ["A corte", "B corte"]
    assert all(s["tenant_id"] == tenant_a for s in data_a)

    services_b = client.get("/v1/services", params={"tenant_id": tenant_b})
    assert services_b.status_code == 200
    data_b = services_b.json()
    assert [s["name"] for s in data_b] == ["Z otro"]
    assert all(s["tenant_id"] == tenant_b for s in data_b)

    # Resources (intentionally out of order)
    client.post("/v1/resources", json={"tenant_id": tenant_a, "name": "Silla 2"})
    client.post("/v1/resources", json={"tenant_id": tenant_a, "name": "Silla 1"})

    resources_a = client.get("/v1/resources", params={"tenant_id": tenant_a})
    assert resources_a.status_code == 200
    resources_data = resources_a.json()
    assert [r["name"] for r in resources_data] == ["Silla 1", "Silla 2"]
    assert all(r["tenant_id"] == tenant_a for r in resources_data)

