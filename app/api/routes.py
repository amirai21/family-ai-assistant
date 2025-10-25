from fastapi import APIRouter
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def get_health() -> HealthResponse:
    return HealthResponse(status="ok")