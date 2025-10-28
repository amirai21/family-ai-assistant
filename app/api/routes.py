from fastapi import APIRouter
from pydantic import BaseModel

from app.api.user_routes import router as user_router
from app.api.family_routes import router as family_router
from app.api.family_member_routes import router as family_member_router
from app.api.task_routes import router as task_router
from app.api.reminder_routes import router as reminder_router
from app.api.recurring_pattern_routes import router as recurring_pattern_router

class HealthResponse(BaseModel):
    status: str

router = APIRouter()

router.include_router(user_router)
router.include_router(family_router)
router.include_router(family_member_router)
router.include_router(task_router)
router.include_router(reminder_router)
router.include_router(recurring_pattern_router)

@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def get_health() -> HealthResponse:
    return HealthResponse(status="ok")