from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    ConflictError,
    DomainError,
    InfrastructureError,
    NotFoundError,
    ValidationError,
)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_payload(
    *,
    code: str,
    message: str,
    details: dict | None,
    request_id: str | None,
) -> dict:
    return {
        "code": code,
        "message": message,
        "details": details,
        "request_id": request_id,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_error_payload(
                code="validation_error",
                message=str(exc),
                details=None,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(
        request: Request, exc: NotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_error_payload(
                code="not_found",
                message=str(exc),
                details=None,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(ConflictError)
    async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=_error_payload(
                code="conflict",
                message=str(exc),
                details=None,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                code="domain_error",
                message=str(exc),
                details=None,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(InfrastructureError)
    async def infrastructure_error_handler(
        request: Request, exc: InfrastructureError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                code="internal_error",
                message=str(exc),
                details=None,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                code="request_validation_error",
                message="Request validation failed",
                details={"errors": exc.errors()},
                request_id=_request_id(request),
            ),
        )
