from fastapi import FastAPI
from app.presentation.http.routers.bookings import router as bookings_router

app = FastAPI(title="Booking Engine", version="0.1.0")
app.include_router(bookings_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to the Chatbot"}
