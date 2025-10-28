from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.timestamps import TimestampMixin
from app.models.enums import TaskStatus
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from app.models.user import User
from datetime import datetime, date
from typing import Optional
from sqlalchemy.dialects.postgresql import JSONB

class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_family_status_due", "family_id", "status", "due_at"),
        Index("ix_tasks_recurring_pattern", "recurring_pattern_id", "occurrence_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Link to recurring pattern if this is a generated instance
    recurring_pattern_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recurring_patterns.id", ondelete="CASCADE"), index=True
    )
    
    # The specific date this task instance is for (if recurring)
    occurrence_date: Mapped[Optional[date]] = mapped_column(Date)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # who created the task (may also be the assignee)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # single-assignee PoC (simple) — flip to many-to-many later if needed
    assignee_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)

    status: Mapped[TaskStatus] = mapped_column(
        PgEnum(TaskStatus, name="task_status"), default=TaskStatus.todo, nullable=False, index=True
    )
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_by: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by_user_id])
    assignee: Mapped[Optional["User"]] = relationship(foreign_keys=[assignee_user_id])
    recurring_pattern: Mapped[Optional["RecurringPattern"]] = relationship(back_populates="tasks")