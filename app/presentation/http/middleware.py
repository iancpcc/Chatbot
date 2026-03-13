import logging
import os
import secrets
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("booking_engine.api")


def register_middlewares(app: FastAPI) -> None:
    cors_allowed_origins = _parse_cors_allowed_origins()
    if cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_allowed_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id
        started = time.perf_counter()

        api_key = _get_configured_api_key()
        if (
            api_key
            and _requires_api_key(path=request.url.path, method=request.method)
            and not _is_valid_api_key(
                expected=api_key,
                provided=request.headers.get("x-api-key"),
            )
        ):
            response = JSONResponse(
                status_code=401,
                content={
                    "code": "unauthorized",
                    "message": "Invalid or missing API key",
                    "details": None,
                    "request_id": request_id,
                },
            )
            response.headers["x-request-id"] = request_id
            return response

        response = await call_next(request)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        tenant_id = request.query_params.get("tenant_id")

        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "tenant_id": tenant_id,
            },
        )
        response.headers["x-request-id"] = request_id
        return response


def _parse_cors_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return []
    return [value.strip() for value in raw.split(",") if value.strip()]


def _get_configured_api_key() -> str | None:
    value = os.getenv("API_KEY", "").strip()
    return value or None


def _normalize_path(path: str) -> str:
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


def _requires_api_key(*, path: str, method: str) -> bool:
    if method.upper() == "OPTIONS":
        return False
    normalized_path = _normalize_path(path)
    if not normalized_path.startswith("/v1/"):
        return False
    return normalized_path != "/v1/health"


def _is_valid_api_key(*, expected: str, provided: str | None) -> bool:
    if provided is None:
        return False
    return secrets.compare_digest(expected, provided.strip())
