from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.timestamps import TimestampMixin
from app.models.enums import RecurrenceFrequency
from sqlalchemy.dialects.postgresql import ENUM as PgEnum, JSONB
from datetime import datetime
from typing import Optional

class RecurringPattern(Base, TimestampMixin):
    """
    Defines a recurring pattern for tasks.
    Examples:
    - Weekly on Sundays at 16:00
    - Daily at 8:00
    - Monthly on the 1st and 15th
    - Every Tuesday and Thursday
    """
    __tablename__ = "recurring_patterns"
    __table_args__ = (
        Index("ix_recurring_patterns_family_active", "family_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Core pattern definition
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Recurrence rules
    frequency: Mapped[RecurrenceFrequency] = mapped_column(
        PgEnum(RecurrenceFrequency, name="recurrence_frequency"), nullable=False
    )
    
    # Interval: every N days/weeks/months (e.g., every 2 weeks)
    interval: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # For weekly: which days of week (0=Monday, 6=Sunday)
    # For monthly: which days of month (1-31)
    # Stored as array: [0, 2, 4] for Mon/Wed/Fri or [1, 15] for 1st and 15th
    by_day: Mapped[Optional[list]] = mapped_column(JSONB)
    
    # Time of day for the task (hour and minute)
    start_time_hour: Mapped[Optional[int]] = mapped_column(Integer)
    start_time_minute: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    
    # Optional: duration in minutes (e.g., 60 for 1 hour task)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Date range for recurrence
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Default assignee for generated tasks
    default_assignee_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Who created this pattern
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Pattern status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    
    # Store last generation date to track what's been generated
    last_generated_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Additional metadata
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    default_assignee: Mapped[Optional["User"]] = relationship(foreign_keys=[default_assignee_user_id])
    created_by: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by_user_id])
    tasks: Mapped[list["Task"]] = relationship(back_populates="recurring_pattern", cascade="all, delete-orphan")

