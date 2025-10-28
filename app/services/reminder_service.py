from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.models.reminder import Reminder as ReminderModel
from app.api.schemas import ReminderCreate, ReminderUpdate

async def get_reminders(
    db: AsyncSession,
    task_id: Optional[int] = None,
    user_id: Optional[int] = None,
    sent: Optional[bool] = None
) -> List[ReminderModel]:
    """Get reminders with optional filters"""
    query = select(ReminderModel).options(selectinload(ReminderModel.user))
    
    filters = []
    if task_id is not None:
        filters.append(ReminderModel.task_id == task_id)
    if user_id is not None:
        filters.append(ReminderModel.user_id == user_id)
    if sent is not None:
        if sent:
            filters.append(ReminderModel.sent_at.isnot(None))
        else:
            filters.append(ReminderModel.sent_at.is_(None))
    
    if filters:
        query = query.where(and_(*filters))
    
    result = await db.execute(query)
    return list(result.scalars().all())

async def get_reminder_by_id(db: AsyncSession, reminder_id: int) -> Optional[ReminderModel]:
    """Get a reminder by ID"""
    result = await db.execute(
        select(ReminderModel)
        .where(ReminderModel.id == reminder_id)
        .options(selectinload(ReminderModel.user))
    )
    return result.scalar_one_or_none()

async def create_reminder(
    db: AsyncSession,
    task_id: int,
    reminder_data: ReminderCreate
) -> ReminderModel:
    """Create a new reminder for a task"""
    # Remove timezone info if present (make naive)
    due_at = reminder_data.due_at.replace(tzinfo=None) if reminder_data.due_at else None
    
    reminder = ReminderModel(
        task_id=task_id,
        user_id=reminder_data.user_id,
        due_at=due_at,
        payload=reminder_data.payload or {},
    )
    db.add(reminder)
    await db.flush()
    await db.refresh(reminder)
    
    # Load user relationship
    await db.refresh(reminder, ["user"])
    return reminder

async def update_reminder(
    db: AsyncSession,
    reminder_id: int,
    reminder_data: ReminderUpdate
) -> Optional[ReminderModel]:
    """Update an existing reminder"""
    reminder = await get_reminder_by_id(db, reminder_id)
    if not reminder:
        return None
    
    if reminder_data.due_at is not None:
        reminder.due_at = reminder_data.due_at.replace(tzinfo=None) if reminder_data.due_at else None
    if reminder_data.sent_at is not None:
        reminder.sent_at = reminder_data.sent_at
    if reminder_data.payload is not None:
        reminder.payload = reminder_data.payload
    
    await db.flush()
    await db.refresh(reminder)
    await db.refresh(reminder, ["user"])
    return reminder

async def delete_reminder(db: AsyncSession, reminder_id: int) -> bool:
    """Delete a reminder"""
    reminder = await get_reminder_by_id(db, reminder_id)
    if not reminder:
        return False
    
    await db.delete(reminder)
    await db.flush()
    return True

async def mark_reminder_sent(db: AsyncSession, reminder_id: int) -> Optional[ReminderModel]:
    """Mark a reminder as sent"""
    reminder = await get_reminder_by_id(db, reminder_id)
    if not reminder:
        return None
    
    reminder.sent_at = datetime.utcnow()
    
    await db.flush()
    await db.refresh(reminder)
    await db.refresh(reminder, ["user"])
    return reminder

async def get_due_reminders(db: AsyncSession, limit: int = 100) -> List[ReminderModel]:
    """Get reminders that are due and haven't been sent yet"""
    result = await db.execute(
        select(ReminderModel)
        .where(
            and_(
                ReminderModel.due_at <= datetime.utcnow(),
                ReminderModel.sent_at.is_(None)
            )
        )
        .options(selectinload(ReminderModel.user))
        .limit(limit)
    )
    return list(result.scalars().all())

async def get_task_reminders(db: AsyncSession, task_id: int) -> List[ReminderModel]:
    """Get all reminders for a specific task"""
    result = await db.execute(
        select(ReminderModel)
        .where(ReminderModel.task_id == task_id)
        .options(selectinload(ReminderModel.user))
        .order_by(ReminderModel.due_at)
    )
    return list(result.scalars().all())

