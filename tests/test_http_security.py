import pytest
from fastapi.testclient import TestClient

from app.main import app, create_app
from app.presentation.http.dependencies import reset_state


def test_v1_endpoints_require_api_key_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "secret-test-key")
    reset_state()

    with TestClient(app) as client:
        response = client.post(
            "/v1/services",
            json={
                "tenant_id": "tenant-sec-1",
                "name": "Corte",
                "duration_minutes": 30,
                "price": 20.0,
            },
        )

    assert response.status_code == 401
    payload = response.json()
    assert payload["code"] == "unauthorized"
    assert payload["message"] == "Invalid or missing API key"
    assert payload["request_id"]
    assert response.headers["x-request-id"] == payload["request_id"]


def test_v1_endpoints_accept_valid_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "secret-test-key")
    reset_state()

    with TestClient(app) as client:
        response = client.post(
            "/v1/services",
            headers={"x-api-key": "secret-test-key"},
            json={
                "tenant_id": "tenant-sec-2",
                "name": "Corte",
                "duration_minutes": 30,
                "price": 20.0,
            },
        )

    assert response.status_code == 200
    assert response.json()["service_id"]


def test_health_endpoints_are_not_blocked_by_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "secret-test-key")
    reset_state()

    with TestClient(app) as client:
        liveness_response = client.get("/health")
        readiness_response = client.get("/v1/health")

    assert liveness_response.status_code == 200
    assert readiness_response.status_code != 401


def test_cors_preflight_allows_configured_origin_without_api_key_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "secret-test-key")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://frontend.example.com")

    app_with_cors = create_app()
    with TestClient(app_with_cors) as client:
        response = client.options(
            "/v1/services",
            headers={
                "Origin": "https://frontend.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://frontend.example.com"
