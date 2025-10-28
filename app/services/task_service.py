from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.models.task import Task as TaskModel
from app.models.enums import TaskStatus
from app.api.schemas import TaskCreate, TaskUpdate

async def get_tasks(
    db: AsyncSession,
    family_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    assignee_user_id: Optional[int] = None
) -> List[TaskModel]:
    """Get tasks with optional filters"""
    query = select(TaskModel).options(
        selectinload(TaskModel.created_by),
        selectinload(TaskModel.assignee)
    )
    
    filters = []
    if family_id is not None:
        filters.append(TaskModel.family_id == family_id)
    if status is not None:
        filters.append(TaskModel.status == status)
    if assignee_user_id is not None:
        filters.append(TaskModel.assignee_user_id == assignee_user_id)
    
    if filters:
        query = query.where(and_(*filters))
    
    result = await db.execute(query)
    return list(result.scalars().all())

async def get_task_by_id(db: AsyncSession, task_id: int) -> Optional[TaskModel]:
    """Get a task by ID with relationships loaded"""
    result = await db.execute(
        select(TaskModel)
        .where(TaskModel.id == task_id)
        .options(
            selectinload(TaskModel.created_by),
            selectinload(TaskModel.assignee)
        )
    )
    return result.scalar_one_or_none()

async def create_task(
    db: AsyncSession,
    task_data: TaskCreate,
    created_by_user_id: Optional[int] = None
) -> TaskModel:
    """Create a new task"""
    # Remove timezone info if present (make naive)
    due_at = task_data.due_at.replace(tzinfo=None) if task_data.due_at else None
    
    task = TaskModel(
        family_id=task_data.family_id,
        title=task_data.title,
        description=task_data.description,
        created_by_user_id=created_by_user_id,
        assignee_user_id=task_data.assignee_user_id,
        status=task_data.status,
        due_at=due_at,
        meta=task_data.meta or {},
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    
    # Load relationships
    await db.refresh(task, ["created_by", "assignee"])
    return task

async def update_task(
    db: AsyncSession,
    task_id: int,
    task_data: TaskUpdate
) -> Optional[TaskModel]:
    """Update an existing task"""
    task = await get_task_by_id(db, task_id)
    if not task:
        return None
    
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.assignee_user_id is not None:
        task.assignee_user_id = task_data.assignee_user_id
    if task_data.status is not None:
        task.status = task_data.status
        # Auto-set completed_at when marking as done
        if task_data.status == TaskStatus.done and not task.completed_at:
            task.completed_at = datetime.utcnow()
    if task_data.due_at is not None:
        task.due_at = task_data.due_at.replace(tzinfo=None) if task_data.due_at else None
    if task_data.completed_at is not None:
        task.completed_at = task_data.completed_at
    if task_data.meta is not None:
        task.meta = task_data.meta
    
    await db.flush()
    await db.refresh(task)
    await db.refresh(task, ["created_by", "assignee"])
    return task

async def delete_task(db: AsyncSession, task_id: int) -> bool:
    """Delete a task"""
    task = await get_task_by_id(db, task_id)
    if not task:
        return False
    
    await db.delete(task)
    await db.flush()
    return True

async def complete_task(db: AsyncSession, task_id: int) -> Optional[TaskModel]:
    """Mark a task as completed"""
    task = await get_task_by_id(db, task_id)
    if not task:
        return None
    
    task.status = TaskStatus.done
    task.completed_at = datetime.utcnow()
    
    await db.flush()
    await db.refresh(task)
    await db.refresh(task, ["created_by", "assignee"])
    return task

async def get_overdue_tasks(db: AsyncSession, family_id: Optional[int] = None) -> List[TaskModel]:
    """Get tasks that are overdue"""
    query = select(TaskModel).where(
        and_(
            TaskModel.due_at < datetime.utcnow(),
            TaskModel.status.in_([TaskStatus.todo, TaskStatus.in_progress])
        )
    ).options(
        selectinload(TaskModel.created_by),
        selectinload(TaskModel.assignee)
    )
    
    if family_id is not None:
        query = query.where(TaskModel.family_id == family_id)
    
    result = await db.execute(query)
    return list(result.scalars().all())

