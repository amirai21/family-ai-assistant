from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from app.models.recurring_pattern import RecurringPattern as RecurringPatternModel
from app.models.task import Task as TaskModel
from app.models.enums import RecurrenceFrequency, TaskStatus
from app.api.schemas import RecurringPatternCreate, RecurringPatternUpdate


async def get_recurring_patterns(
    db: AsyncSession,
    family_id: Optional[int] = None,
    is_active: Optional[bool] = None
) -> List[RecurringPatternModel]:
    """Get recurring patterns with optional filters"""
    query = select(RecurringPatternModel).options(
        selectinload(RecurringPatternModel.default_assignee),
        selectinload(RecurringPatternModel.created_by)
    )
    
    filters = []
    if family_id is not None:
        filters.append(RecurringPatternModel.family_id == family_id)
    if is_active is not None:
        filters.append(RecurringPatternModel.is_active == is_active)
    
    if filters:
        query = query.where(and_(*filters))
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recurring_pattern_by_id(
    db: AsyncSession, 
    pattern_id: int
) -> Optional[RecurringPatternModel]:
    """Get a recurring pattern by ID with relationships loaded"""
    result = await db.execute(
        select(RecurringPatternModel)
        .where(RecurringPatternModel.id == pattern_id)
        .options(
            selectinload(RecurringPatternModel.default_assignee),
            selectinload(RecurringPatternModel.created_by)
        )
    )
    return result.scalar_one_or_none()


async def create_recurring_pattern(
    db: AsyncSession,
    pattern_data: RecurringPatternCreate,
    created_by_user_id: Optional[int] = None
) -> RecurringPatternModel:
    """Create a new recurring pattern"""
    # Remove timezone info if present
    start_date = pattern_data.start_date.replace(tzinfo=None) if pattern_data.start_date else None
    end_date = pattern_data.end_date.replace(tzinfo=None) if pattern_data.end_date else None
    
    pattern = RecurringPatternModel(
        family_id=pattern_data.family_id,
        title=pattern_data.title,
        description=pattern_data.description,
        frequency=pattern_data.frequency,
        interval=pattern_data.interval,
        by_day=pattern_data.by_day,
        start_time_hour=pattern_data.start_time_hour,
        start_time_minute=pattern_data.start_time_minute,
        duration_minutes=pattern_data.duration_minutes,
        start_date=start_date,
        end_date=end_date,
        default_assignee_user_id=pattern_data.default_assignee_user_id,
        created_by_user_id=created_by_user_id,
        is_active=pattern_data.is_active,
        meta=pattern_data.meta or {},
    )
    
    db.add(pattern)
    await db.flush()
    await db.refresh(pattern)
    
    # Load relationships
    await db.refresh(pattern, ["default_assignee", "created_by"])
    return pattern


async def update_recurring_pattern(
    db: AsyncSession,
    pattern_id: int,
    pattern_data: RecurringPatternUpdate
) -> Optional[RecurringPatternModel]:
    """Update an existing recurring pattern"""
    pattern = await get_recurring_pattern_by_id(db, pattern_id)
    if not pattern:
        return None
    
    if pattern_data.title is not None:
        pattern.title = pattern_data.title
    if pattern_data.description is not None:
        pattern.description = pattern_data.description
    if pattern_data.frequency is not None:
        pattern.frequency = pattern_data.frequency
    if pattern_data.interval is not None:
        pattern.interval = pattern_data.interval
    if pattern_data.by_day is not None:
        pattern.by_day = pattern_data.by_day
    if pattern_data.start_time_hour is not None:
        pattern.start_time_hour = pattern_data.start_time_hour
    if pattern_data.start_time_minute is not None:
        pattern.start_time_minute = pattern_data.start_time_minute
    if pattern_data.duration_minutes is not None:
        pattern.duration_minutes = pattern_data.duration_minutes
    if pattern_data.start_date is not None:
        pattern.start_date = pattern_data.start_date.replace(tzinfo=None)
    if pattern_data.end_date is not None:
        pattern.end_date = pattern_data.end_date.replace(tzinfo=None) if pattern_data.end_date else None
    if pattern_data.default_assignee_user_id is not None:
        pattern.default_assignee_user_id = pattern_data.default_assignee_user_id
    if pattern_data.is_active is not None:
        pattern.is_active = pattern_data.is_active
    if pattern_data.meta is not None:
        pattern.meta = pattern_data.meta
    
    await db.flush()
    await db.refresh(pattern)
    await db.refresh(pattern, ["default_assignee", "created_by"])
    return pattern


async def delete_recurring_pattern(
    db: AsyncSession, 
    pattern_id: int,
    delete_future_tasks: bool = False
) -> bool:
    """
    Delete a recurring pattern.
    If delete_future_tasks is True, also deletes all future task instances.
    """
    pattern = await get_recurring_pattern_by_id(db, pattern_id)
    if not pattern:
        return False
    
    if delete_future_tasks:
        # Delete all future tasks (not completed) for this pattern
        future_tasks = await db.execute(
            select(TaskModel).where(
                and_(
                    TaskModel.recurring_pattern_id == pattern_id,
                    TaskModel.status.in_([TaskStatus.todo, TaskStatus.in_progress]),
                    TaskModel.due_at >= datetime.utcnow()
                )
            )
        )
        for task in future_tasks.scalars().all():
            await db.delete(task)
    
    await db.delete(pattern)
    await db.flush()
    return True


def _get_next_occurrence_date(
    current_date: date,
    frequency: RecurrenceFrequency,
    interval: int,
    by_day: Optional[list[int]] = None
) -> Optional[date]:
    """
    Calculate the next occurrence date based on frequency and rules.
    
    Args:
        current_date: The current/last occurrence date
        frequency: daily, weekly, monthly, yearly
        interval: Repeat every N periods
        by_day: For weekly: days of week (0=Mon, 6=Sun), For monthly: days of month (1-31)
    
    Returns:
        The next occurrence date, or None if no more occurrences
    """
    if frequency == RecurrenceFrequency.daily:
        return current_date + timedelta(days=interval)
    
    elif frequency == RecurrenceFrequency.weekly:
        if not by_day:
            # If no specific days, just add interval weeks
            return current_date + timedelta(weeks=interval)
        
        # Find next occurrence in the by_day list
        current_weekday = current_date.weekday()  # 0=Monday, 6=Sunday
        
        # Sort by_day to ensure we check in order
        sorted_days = sorted(by_day)
        
        # Look for next day in current week
        for day in sorted_days:
            if day > current_weekday:
                days_ahead = day - current_weekday
                return current_date + timedelta(days=days_ahead)
        
        # No more days this week, move to next occurrence (interval weeks ahead)
        # Go to first day in by_day list
        first_day = sorted_days[0]
        days_to_next_week = 7 - current_weekday + first_day
        weeks_to_add = interval - 1  # We already moved to next week
        return current_date + timedelta(days=days_to_next_week) + timedelta(weeks=weeks_to_add)
    
    elif frequency == RecurrenceFrequency.monthly:
        if not by_day:
            # If no specific days, use the same day of month
            return current_date + relativedelta(months=interval)
        
        # Find next occurrence in the by_day list (days of month)
        current_day = current_date.day
        sorted_days = sorted(by_day)
        
        # Look for next day in current month
        for day in sorted_days:
            if day > current_day:
                try:
                    return current_date.replace(day=day)
                except ValueError:
                    # Day doesn't exist in this month (e.g., 31st in February)
                    continue
        
        # No more days this month, move to next month(s)
        next_month = current_date + relativedelta(months=interval)
        # Try to use first day in by_day list
        for day in sorted_days:
            try:
                return next_month.replace(day=day)
            except ValueError:
                continue
        
        # If all days fail, use last day of month
        return next_month
    
    elif frequency == RecurrenceFrequency.yearly:
        return current_date + relativedelta(years=interval)
    
    return None


async def generate_task_instances(
    db: AsyncSession,
    pattern_id: int,
    generate_until: datetime,
    max_instances: int = 100
) -> List[TaskModel]:
    """
    Generate task instances for a recurring pattern up to a certain date.
    
    Args:
        db: Database session
        pattern_id: The recurring pattern ID
        generate_until: Generate tasks up to this date
        max_instances: Maximum number of instances to generate in one call
    
    Returns:
        List of created task instances
    """
    pattern = await get_recurring_pattern_by_id(db, pattern_id)
    if not pattern or not pattern.is_active:
        return []
    
    # Determine start point
    if pattern.last_generated_until:
        start_from = pattern.last_generated_until
    else:
        start_from = pattern.start_date
    
    # Don't generate beyond end_date if set
    if pattern.end_date and generate_until > pattern.end_date:
        generate_until = pattern.end_date
    
    if start_from >= generate_until:
        return []
    
    # Generate occurrences
    created_tasks = []
    current_date = start_from.date() if isinstance(start_from, datetime) else start_from
    generate_until_date = generate_until.date() if isinstance(generate_until, datetime) else generate_until
    
    count = 0
    while current_date <= generate_until_date and count < max_instances:
        # Check if this date should have an occurrence
        should_generate = _should_generate_on_date(
            current_date, 
            pattern.start_date.date(),
            pattern.frequency,
            pattern.interval,
            pattern.by_day
        )
        
        if should_generate:
            # Check if task already exists for this date
            existing = await db.execute(
                select(TaskModel).where(
                    and_(
                        TaskModel.recurring_pattern_id == pattern_id,
                        TaskModel.occurrence_date == current_date
                    )
                )
            )
            if not existing.scalar_one_or_none():
                # Create task instance
                task = await _create_task_instance(db, pattern, current_date)
                created_tasks.append(task)
                count += 1
        
        # Move to next day to check
        current_date += timedelta(days=1)
    
    # Update last_generated_until
    pattern.last_generated_until = generate_until
    await db.flush()
    
    return created_tasks


def _should_generate_on_date(
    check_date: date,
    start_date: date,
    frequency: RecurrenceFrequency,
    interval: int,
    by_day: Optional[list[int]]
) -> bool:
    """Check if a task should be generated on a specific date"""
    if check_date < start_date:
        return False
    
    if frequency == RecurrenceFrequency.daily:
        days_diff = (check_date - start_date).days
        return days_diff % interval == 0
    
    elif frequency == RecurrenceFrequency.weekly:
        if not by_day:
            # Weekly on same day
            days_diff = (check_date - start_date).days
            return days_diff % (interval * 7) == 0
        
        # Check if this day of week is in by_day
        weekday = check_date.weekday()
        if weekday not in by_day:
            return False
        
        # Check if we're in the right week interval
        weeks_diff = (check_date - start_date).days // 7
        return weeks_diff % interval == 0
    
    elif frequency == RecurrenceFrequency.monthly:
        if not by_day:
            # Monthly on same day of month
            months_diff = (check_date.year - start_date.year) * 12 + (check_date.month - start_date.month)
            return months_diff % interval == 0 and check_date.day == start_date.day
        
        # Check if this day of month is in by_day
        if check_date.day not in by_day:
            return False
        
        # Check if we're in the right month interval
        months_diff = (check_date.year - start_date.year) * 12 + (check_date.month - start_date.month)
        return months_diff % interval == 0
    
    elif frequency == RecurrenceFrequency.yearly:
        years_diff = check_date.year - start_date.year
        return (years_diff % interval == 0 and 
                check_date.month == start_date.month and 
                check_date.day == start_date.day)
    
    return False


async def _create_task_instance(
    db: AsyncSession,
    pattern: RecurringPatternModel,
    occurrence_date: date
) -> TaskModel:
    """Create a single task instance from a recurring pattern"""
    # Calculate due datetime
    due_datetime = None
    if pattern.start_time_hour is not None:
        due_datetime = datetime.combine(
            occurrence_date,
            datetime.min.time().replace(
                hour=pattern.start_time_hour,
                minute=pattern.start_time_minute or 0
            )
        )
    
    task = TaskModel(
        family_id=pattern.family_id,
        recurring_pattern_id=pattern.id,
        occurrence_date=occurrence_date,
        title=pattern.title,
        description=pattern.description,
        assignee_user_id=pattern.default_assignee_user_id,
        created_by_user_id=pattern.created_by_user_id,
        status=TaskStatus.todo,
        due_at=due_datetime,
        meta={
            **pattern.meta,
            "generated_from_pattern": True,
            "duration_minutes": pattern.duration_minutes
        }
    )
    
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def get_tasks_for_pattern(
    db: AsyncSession,
    pattern_id: int,
    include_completed: bool = False
) -> List[TaskModel]:
    """Get all task instances for a recurring pattern"""
    query = select(TaskModel).where(
        TaskModel.recurring_pattern_id == pattern_id
    ).options(
        selectinload(TaskModel.assignee),
        selectinload(TaskModel.created_by)
    )
    
    if not include_completed:
        query = query.where(TaskModel.status != TaskStatus.done)
    
    result = await db.execute(query)
    return list(result.scalars().all())


