from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.api.schemas import (
    RecurringPattern, 
    RecurringPatternCreate, 
    RecurringPatternUpdate, 
    RecurringPatternWithDetails,
    TaskWithDetails
)
from app.core.database import get_db
from app.services import recurring_pattern_service, family_service, user_service

router = APIRouter(prefix="/recurring-patterns", tags=["recurring-patterns"])


@router.get("", response_model=List[RecurringPatternWithDetails])
async def get_recurring_patterns(
    family_id: Optional[int] = Query(None, description="Filter by family ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
) -> List[RecurringPatternWithDetails]:
    """Get recurring patterns with optional filters"""
    patterns = await recurring_pattern_service.get_recurring_patterns(
        db,
        family_id=family_id,
        is_active=is_active
    )
    return patterns


@router.get("/{pattern_id}", response_model=RecurringPatternWithDetails)
async def get_recurring_pattern(
    pattern_id: int, 
    db: AsyncSession = Depends(get_db)
) -> RecurringPatternWithDetails:
    """Get a specific recurring pattern by ID"""
    pattern = await recurring_pattern_service.get_recurring_pattern_by_id(db, pattern_id)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring pattern with id {pattern_id} not found"
        )
    return pattern


@router.post("", response_model=RecurringPatternWithDetails, status_code=status.HTTP_201_CREATED)
async def create_recurring_pattern(
    pattern_data: RecurringPatternCreate,
    db: AsyncSession = Depends(get_db)
) -> RecurringPatternWithDetails:
    """Create a new recurring pattern"""
    # Verify family exists
    family = await family_service.get_family_by_id(db, pattern_data.family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family with id {pattern_data.family_id} not found"
        )
    
    # Verify default assignee exists if provided
    if pattern_data.default_assignee_user_id:
        assignee = await user_service.get_user_by_id(db, pattern_data.default_assignee_user_id)
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {pattern_data.default_assignee_user_id} not found"
            )
    
    # Verify creator exists if provided
    if pattern_data.created_by_user_id:
        creator = await user_service.get_user_by_id(db, pattern_data.created_by_user_id)
        if not creator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Creator user with id {pattern_data.created_by_user_id} not found"
            )
    
    pattern = await recurring_pattern_service.create_recurring_pattern(
        db, 
        pattern_data, 
        pattern_data.created_by_user_id
    )
    
    # Auto-generate initial tasks (next 30 days by default)
    generate_until = datetime.utcnow() + timedelta(days=30)
    await recurring_pattern_service.generate_task_instances(db, pattern.id, generate_until)
    await db.commit()
    
    return pattern


@router.put("/{pattern_id}", response_model=RecurringPatternWithDetails)
async def update_recurring_pattern(
    pattern_id: int,
    pattern_data: RecurringPatternUpdate,
    db: AsyncSession = Depends(get_db)
) -> RecurringPatternWithDetails:
    """Update an existing recurring pattern"""
    # Verify default assignee exists if being changed
    if pattern_data.default_assignee_user_id:
        assignee = await user_service.get_user_by_id(db, pattern_data.default_assignee_user_id)
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {pattern_data.default_assignee_user_id} not found"
            )
    
    pattern = await recurring_pattern_service.update_recurring_pattern(db, pattern_id, pattern_data)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring pattern with id {pattern_id} not found"
        )
    
    await db.commit()
    return pattern


@router.delete("/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring_pattern(
    pattern_id: int,
    delete_future_tasks: bool = Query(False, description="Also delete future task instances"),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a recurring pattern"""
    deleted = await recurring_pattern_service.delete_recurring_pattern(
        db, 
        pattern_id, 
        delete_future_tasks
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring pattern with id {pattern_id} not found"
        )
    
    await db.commit()


@router.post("/{pattern_id}/generate", response_model=List[TaskWithDetails])
async def generate_task_instances(
    pattern_id: int,
    days_ahead: int = Query(30, ge=1, le=365, description="Generate tasks for next N days"),
    db: AsyncSession = Depends(get_db)
) -> List[TaskWithDetails]:
    """
    Manually trigger generation of task instances for a recurring pattern.
    This is useful for generating tasks further into the future.
    """
    pattern = await recurring_pattern_service.get_recurring_pattern_by_id(db, pattern_id)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring pattern with id {pattern_id} not found"
        )
    
    generate_until = datetime.utcnow() + timedelta(days=days_ahead)
    tasks = await recurring_pattern_service.generate_task_instances(db, pattern_id, generate_until)
    await db.commit()
    
    return tasks


@router.get("/{pattern_id}/tasks", response_model=List[TaskWithDetails])
async def get_pattern_tasks(
    pattern_id: int,
    include_completed: bool = Query(False, description="Include completed tasks"),
    db: AsyncSession = Depends(get_db)
) -> List[TaskWithDetails]:
    """Get all task instances for a recurring pattern"""
    pattern = await recurring_pattern_service.get_recurring_pattern_by_id(db, pattern_id)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring pattern with id {pattern_id} not found"
        )
    
    tasks = await recurring_pattern_service.get_tasks_for_pattern(
        db, 
        pattern_id, 
        include_completed
    )
    return tasks


@router.patch("/{pattern_id}/activate", response_model=RecurringPatternWithDetails)
async def activate_recurring_pattern(
    pattern_id: int,
    db: AsyncSession = Depends(get_db)
) -> RecurringPatternWithDetails:
    """Activate a recurring pattern and generate upcoming tasks"""
    pattern = await recurring_pattern_service.get_recurring_pattern_by_id(db, pattern_id)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring pattern with id {pattern_id} not found"
        )
    
    pattern.is_active = True
    await db.flush()
    
    # Generate tasks for next 30 days
    generate_until = datetime.utcnow() + timedelta(days=30)
    await recurring_pattern_service.generate_task_instances(db, pattern.id, generate_until)
    await db.commit()
    
    await db.refresh(pattern)
    await db.refresh(pattern, ["default_assignee", "created_by"])
    return pattern


@router.patch("/{pattern_id}/deactivate", response_model=RecurringPatternWithDetails)
async def deactivate_recurring_pattern(
    pattern_id: int,
    db: AsyncSession = Depends(get_db)
) -> RecurringPatternWithDetails:
    """Deactivate a recurring pattern (stops generating new tasks)"""
    pattern = await recurring_pattern_service.get_recurring_pattern_by_id(db, pattern_id)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring pattern with id {pattern_id} not found"
        )
    
    pattern.is_active = False
    await db.flush()
    await db.commit()
    
    await db.refresh(pattern)
    await db.refresh(pattern, ["default_assignee", "created_by"])
    return pattern


