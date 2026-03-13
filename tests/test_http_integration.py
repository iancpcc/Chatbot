from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.presentation.http.dependencies import reset_state

API_PREFIX = "/v1"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _create_service(client: TestClient, tenant_id: str, name: str = "Corte") -> str:
    response = client.post(
        f"{API_PREFIX}/services",
        json={
            "tenant_id": tenant_id,
            "name": name,
            "duration_minutes": 30,
            "price": 20.0,
        },
    )
    assert response.status_code == 200
    return response.json()["service_id"]


def _create_resource(client: TestClient, tenant_id: str, name: str = "Silla 1") -> str:
    response = client.post(
        f"{API_PREFIX}/resources",
        json={
            "tenant_id": tenant_id,
            "name": name,
        },
    )
    assert response.status_code == 200
    return response.json()["resource_id"]


def _create_booking(
    client: TestClient,
    tenant_id: str,
    service_id: str,
    resource_id: str | None,
    start: datetime,
    end: datetime,
) -> dict:
    payload = {
        "tenant_id": tenant_id,
        "service_id": service_id,
        "customer_name": "Ana",
        "customer_contact": "+34123456789",
        "start": _iso(start),
        "end": _iso(end),
    }
    if resource_id is not None:
        payload["resource_id"] = resource_id
    response = client.post(
        f"{API_PREFIX}/bookings",
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


def test_http_catalog_and_booking_happy_path() -> None:
    reset_state()
    client = TestClient(app)
    tenant_id = "tenant-http-1"

    service_id = _create_service(client, tenant_id)
    resource_id = _create_resource(client, tenant_id)

    response = _create_booking(
        client=client,
        tenant_id=tenant_id,
        service_id=service_id,
        resource_id=resource_id,
        start=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 1, 10, 30, tzinfo=timezone.utc),
    )

    assert response["status"] == "pending"
    assert "booking_id" in response


def test_http_booking_not_found_when_service_missing() -> None:
    reset_state()
    client = TestClient(app)
    tenant_id = "tenant-http-2"
    resource_id = _create_resource(client, tenant_id)

    response = client.post(
        f"{API_PREFIX}/bookings",
        json={
            "tenant_id": tenant_id,
            "service_id": "11111111-1111-1111-1111-999999999999",
            "resource_id": resource_id,
            "customer_name": "Ana",
            "customer_contact": "+34123456789",
            "start": "2026-03-01T10:00:00Z",
            "end": "2026-03-01T10:30:00Z",
        },
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert response.json()["message"] == "Service not found"
    assert "request_id" in response.json()


def test_http_booking_conflict_on_overlap() -> None:
    reset_state()
    client = TestClient(app)
    tenant_id = "tenant-http-3"
    service_id = _create_service(client, tenant_id)
    resource_id = _create_resource(client, tenant_id)

    _create_booking(
        client=client,
        tenant_id=tenant_id,
        service_id=service_id,
        resource_id=resource_id,
        start=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 1, 10, 30, tzinfo=timezone.utc),
    )

    response = client.post(
        f"{API_PREFIX}/bookings",
        json={
            "tenant_id": tenant_id,
            "service_id": service_id,
            "resource_id": resource_id,
            "customer_name": "Luis",
            "customer_contact": "+34111111111",
            "start": "2026-03-01T10:15:00Z",
            "end": "2026-03-01T10:45:00Z",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
    assert response.json()["message"] == "Time slot not available"


def test_http_booking_validation_error_when_start_after_end() -> None:
    reset_state()
    client = TestClient(app)
    tenant_id = "tenant-http-4"
    service_id = _create_service(client, tenant_id)
    resource_id = _create_resource(client, tenant_id)

    response = client.post(
        f"{API_PREFIX}/bookings",
        json={
            "tenant_id": tenant_id,
            "service_id": service_id,
            "resource_id": resource_id,
            "customer_name": "Ana",
            "customer_contact": "+34123456789",
            "start": "2026-03-01T10:30:00Z",
            "end": "2026-03-01T10:00:00Z",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert response.json()["message"] == "Start must be before end"


def test_http_list_bookings_supports_filters_and_order() -> None:
    reset_state()
    client = TestClient(app)
    tenant_id = "tenant-http-5"
    service_id = _create_service(client, tenant_id)
    resource_id = _create_resource(client, tenant_id)

    _create_booking(
        client=client,
        tenant_id=tenant_id,
        service_id=service_id,
        resource_id=resource_id,
        start=datetime(2026, 3, 1, 11, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 1, 11, 30, tzinfo=timezone.utc),
    )
    _create_booking(
        client=client,
        tenant_id=tenant_id,
        service_id=service_id,
        resource_id=resource_id,
        start=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 1, 10, 30, tzinfo=timezone.utc),
    )

    response = client.get(
        f"{API_PREFIX}/bookings",
        params={
            "tenant_id": tenant_id,
            "resource_id": resource_id,
            "start_from": "2026-03-01T09:00:00Z",
            "end_to": "2026-03-01T12:00:00Z",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["start"] == "2026-03-01T10:00:00Z"
    assert data[1]["start"] == "2026-03-01T11:00:00Z"


def test_http_get_booking_by_id_and_cancel() -> None:
    reset_state()
    client = TestClient(app)
    tenant_id = "tenant-http-6"
    service_id = _create_service(client, tenant_id)
    resource_id = _create_resource(client, tenant_id)
    created = _create_booking(
        client=client,
        tenant_id=tenant_id,
        service_id=service_id,
        resource_id=resource_id,
        start=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 1, 12, 30, tzinfo=timezone.utc),
    )

    booking_id = created["booking_id"]
    get_response = client.get(
        f"{API_PREFIX}/bookings/{booking_id}",
        params={"tenant_id": tenant_id},
    )
    assert get_response.status_code == 200
    assert get_response.json()["booking_id"] == booking_id
    assert get_response.json()["status"] == "pending"

    cancel_response = client.patch(
        f"{API_PREFIX}/bookings/{booking_id}/cancel",
        params={"tenant_id": tenant_id},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"


def test_http_booking_duration_must_match_service() -> None:
    reset_state()
    client = TestClient(app)
    tenant_id = "tenant-http-7"
    service_id = _create_service(client, tenant_id)
    resource_id = _create_resource(client, tenant_id)

    response = client.post(
        f"{API_PREFIX}/bookings",
        json={
            "tenant_id": tenant_id,
            "service_id": service_id,
            "resource_id": resource_id,
            "customer_name": "Ana",
            "customer_contact": "+34123456789",
            "start": "2026-03-01T10:00:00Z",
            "end": "2026-03-01T10:45:00Z",
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_http_multi_tenant_isolation_for_get_and_cancel() -> None:
    reset_state()
    client = TestClient(app)
    tenant_a = "tenant-http-8a"
    tenant_b = "tenant-http-8b"

    service_id = _create_service(client, tenant_a)
    resource_id = _create_resource(client, tenant_a)
    created = _create_booking(
        client=client,
        tenant_id=tenant_a,
        service_id=service_id,
        resource_id=resource_id,
        start=datetime(2026, 3, 1, 13, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 1, 13, 30, tzinfo=timezone.utc),
    )
    booking_id = created["booking_id"]

    get_response = client.get(
        f"{API_PREFIX}/bookings/{booking_id}",
        params={"tenant_id": tenant_b},
    )
    assert get_response.status_code == 404
    assert get_response.json()["code"] == "not_found"

    cancel_response = client.patch(
        f"{API_PREFIX}/bookings/{booking_id}/cancel",
        params={"tenant_id": tenant_b},
    )
    assert cancel_response.status_code == 404
    assert cancel_response.json()["code"] == "not_found"


def test_http_booking_can_be_created_without_resource_id() -> None:
    reset_state()
    client = TestClient(app)
    tenant_id = "tenant-http-no-resource"
    service_id = _create_service(client, tenant_id, name="Manicure")
    resource_id = _create_resource(client, tenant_id, name="Mesa 1")

    created = _create_booking(
        client=client,
        tenant_id=tenant_id,
        service_id=service_id,
        resource_id=None,
        start=datetime(2026, 3, 1, 14, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 1, 14, 30, tzinfo=timezone.utc),
    )
    booking_id = created["booking_id"]

    get_response = client.get(
        f"{API_PREFIX}/bookings/{booking_id}",
        params={"tenant_id": tenant_id},
    )
    assert get_response.status_code == 200
    assert get_response.json()["resource_id"] == resource_id
