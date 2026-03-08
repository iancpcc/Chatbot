from pydantic import BaseModel


class ReadinessResponse(BaseModel):
    status: str
    api: str
    database: str
    llm_provider: str
    llm_configured: bool

