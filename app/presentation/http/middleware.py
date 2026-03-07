import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request

logger = logging.getLogger("booking_engine.api")


def register_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id
        started = time.perf_counter()

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
