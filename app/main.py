import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.presentation.http.dependencies import reset_state
from app.presentation.http.error_handlers import register_exception_handlers
from app.presentation.http.middleware import register_middlewares
from app.presentation.http.routers.bookings import router as bookings_router
from app.presentation.http.routers.catalog import router as catalog_router
from app.presentation.http.routers.chat import router as chat_router
from app.presentation.http.routers.health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    reset_state()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Booking Engine", version="0.1.0", lifespan=lifespan)
    register_middlewares(app)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(bookings_router, prefix="/v1")
    app.include_router(catalog_router, prefix="/v1")
    app.include_router(chat_router, prefix="/v1")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Welcome to the Chatbot"}

    return app


app = create_app()
