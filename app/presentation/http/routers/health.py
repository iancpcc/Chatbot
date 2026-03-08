import os

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.domain.exceptions import InfrastructureError
from app.infrastructure.persistence.sqlalchemy_database import engine
from app.infrastructure.providers.llm.factory import resolve_llm_provider
from app.presentation.http.schemas.health_schema import ReadinessResponse


router = APIRouter(tags=["Health"])


@router.get("/health")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/health", response_model=ReadinessResponse)
def readiness(response: Response) -> ReadinessResponse:
    db_status = "up"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"

    try:
        llm_provider = resolve_llm_provider()
    except InfrastructureError:
        llm_provider = "unknown"

    llm_configured = _is_llm_configured(llm_provider)
    is_ok = db_status == "up" and llm_configured
    response.status_code = status.HTTP_200_OK if is_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ok" if is_ok else "degraded",
        api="up",
        database=db_status,
        llm_provider=llm_provider,
        llm_configured=llm_configured,
    )


def _is_llm_configured(provider: str) -> bool:
    if provider == "ollama":
        return bool(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip())
    if provider == "groq":
        return bool(os.getenv("GROQ_API_KEY", "").strip())
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        return bool(key and key not in {"your_key_here", "your_openai_key_here"})
    return False

