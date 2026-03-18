import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.presentation.http.dependencies import reset_state

@pytest.fixture(autouse=True)
def mock_external_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    # Evitar migraciones y seeding con conexion real
    monkeypatch.setenv("AUTO_APPLY_MIGRATIONS", "false")
    monkeypatch.setenv("SEED_DEMO_DATA", "false")
    
    # Mockear engine en el router de health
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    monkeypatch.setattr("app.presentation.http.routers.health.engine", mock_engine)


def test_chat_health_ok_with_default_ollama(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    reset_state()
    with TestClient(app) as client:
        response = client.get("/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["api"] == "up"
    assert payload["database"] == "up"
    assert payload["llm_provider"] == "ollama"
    assert payload["llm_configured"] is True


def test_chat_health_degraded_when_openai_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    # Also we should mock that DB is UP to be consistent, or if we want it down:
    # The fixture already mocks it as UP (no exception raised).

    reset_state()
    with TestClient(app) as client:
        response = client.get("/v1/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["api"] == "up"
    assert payload["database"] == "up"
    assert payload["llm_provider"] == "openai"
    assert payload["llm_configured"] is False


def test_liveness_health_is_always_up() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

