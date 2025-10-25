from fastapi import APIRouter
from pydantic import BaseModel

from app.api.user_routes import router as user_router

class HealthResponse(BaseModel):
    status: str

router = APIRouter()

router.include_router(user_router)

@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def get_health() -> HealthResponse:
    return HealthResponse(status="ok")