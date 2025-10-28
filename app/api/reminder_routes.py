from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import Reminder, ReminderCreate, ReminderUpdate, ReminderWithUser
from app.core.database import get_db
from app.services import reminder_service, task_service, user_service

router = APIRouter(tags=["reminders"])

@router.get("/reminders", response_model=List[ReminderWithUser])
async def get_reminders(
    task_id: Optional[int] = Query(None, description="Filter by task ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    sent: Optional[bool] = Query(None, description="Filter by sent status"),
    db: AsyncSession = Depends(get_db)
) -> List[ReminderWithUser]:
    """Get reminders with optional filters"""
    reminders = await reminder_service.get_reminders(
        db,
        task_id=task_id,
        user_id=user_id,
        sent=sent
    )
    return reminders

@router.get("/reminders/due", response_model=List[ReminderWithUser])
async def get_due_reminders(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of reminders to return"),
    db: AsyncSession = Depends(get_db)
) -> List[ReminderWithUser]:
    """Get reminders that are due and haven't been sent yet"""
    reminders = await reminder_service.get_due_reminders(db, limit=limit)
    return reminders

@router.get("/reminders/{reminder_id}", response_model=ReminderWithUser)
async def get_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db)
) -> ReminderWithUser:
    """Get a specific reminder by ID"""
    reminder = await reminder_service.get_reminder_by_id(db, reminder_id)
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder with id {reminder_id} not found"
        )
    return reminder

@router.get("/tasks/{task_id}/reminders", response_model=List[ReminderWithUser])
async def get_task_reminders(
    task_id: int,
    db: AsyncSession = Depends(get_db)
) -> List[ReminderWithUser]:
    """Get all reminders for a specific task"""
    # Verify task exists
    task = await task_service.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    
    reminders = await reminder_service.get_task_reminders(db, task_id)
    return reminders

@router.post("/tasks/{task_id}/reminders", response_model=ReminderWithUser, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    task_id: int,
    reminder_data: ReminderCreate,
    db: AsyncSession = Depends(get_db)
) -> ReminderWithUser:
    """Create a new reminder for a task"""
    # Verify task exists
    task = await task_service.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    
    # Verify user exists
    user = await user_service.get_user_by_id(db, reminder_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {reminder_data.user_id} not found"
        )
    
    reminder = await reminder_service.create_reminder(db, task_id, reminder_data)
    return reminder

@router.put("/reminders/{reminder_id}", response_model=ReminderWithUser)
async def update_reminder(
    reminder_id: int,
    reminder_data: ReminderUpdate,
    db: AsyncSession = Depends(get_db)
) -> ReminderWithUser:
    """Update an existing reminder"""
    reminder = await reminder_service.update_reminder(db, reminder_id, reminder_data)
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder with id {reminder_id} not found"
        )
    return reminder

@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a reminder"""
    deleted = await reminder_service.delete_reminder(db, reminder_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder with id {reminder_id} not found"
        )

@router.post("/reminders/{reminder_id}/mark-sent", response_model=ReminderWithUser)
async def mark_reminder_sent(
    reminder_id: int,
    db: AsyncSession = Depends(get_db)
) -> ReminderWithUser:
    """Mark a reminder as sent"""
    reminder = await reminder_service.mark_reminder_sent(db, reminder_id)
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder with id {reminder_id} not found"
        )
    return reminder

