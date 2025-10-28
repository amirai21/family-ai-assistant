from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import Task, TaskCreate, TaskUpdate, TaskWithDetails
from app.core.database import get_db
from app.services import task_service, family_service, user_service
from app.models.enums import TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("", response_model=List[TaskWithDetails])
async def get_tasks(
    family_id: Optional[int] = Query(None, description="Filter by family ID"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    assignee_user_id: Optional[int] = Query(None, description="Filter by assignee"),
    db: AsyncSession = Depends(get_db)
) -> List[TaskWithDetails]:
    """Get tasks with optional filters"""
    tasks = await task_service.get_tasks(
        db,
        family_id=family_id,
        status=status,
        assignee_user_id=assignee_user_id
    )
    return tasks

@router.get("/overdue", response_model=List[TaskWithDetails])
async def get_overdue_tasks(
    family_id: Optional[int] = Query(None, description="Filter by family ID"),
    db: AsyncSession = Depends(get_db)
) -> List[TaskWithDetails]:
    """Get tasks that are overdue"""
    tasks = await task_service.get_overdue_tasks(db, family_id=family_id)
    return tasks

@router.get("/{task_id}", response_model=TaskWithDetails)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)) -> TaskWithDetails:
    """Get a specific task by ID"""
    task = await task_service.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    return task

@router.post("", response_model=TaskWithDetails, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db)
) -> TaskWithDetails:
    """Create a new task"""
    # Verify family exists
    family = await family_service.get_family_by_id(db, task_data.family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family with id {task_data.family_id} not found"
        )
    
    # Verify assignee exists if provided
    if task_data.assignee_user_id:
        assignee = await user_service.get_user_by_id(db, task_data.assignee_user_id)
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {task_data.assignee_user_id} not found"
            )
    
    # Verify creator exists if provided
    if task_data.created_by_user_id:
        creator = await user_service.get_user_by_id(db, task_data.created_by_user_id)
        if not creator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Creator user with id {task_data.created_by_user_id} not found"
            )
    
    task = await task_service.create_task(db, task_data, task_data.created_by_user_id)
    return task

@router.put("/{task_id}", response_model=TaskWithDetails)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db)
) -> TaskWithDetails:
    """Update an existing task"""
    # Verify assignee exists if being changed
    if task_data.assignee_user_id:
        assignee = await user_service.get_user_by_id(db, task_data.assignee_user_id)
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {task_data.assignee_user_id} not found"
            )
    
    task = await task_service.update_task(db, task_id, task_data)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a task"""
    deleted = await task_service.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

@router.post("/{task_id}/complete", response_model=TaskWithDetails)
async def complete_task(task_id: int, db: AsyncSession = Depends(get_db)) -> TaskWithDetails:
    """Mark a task as completed"""
    task = await task_service.complete_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    return task

