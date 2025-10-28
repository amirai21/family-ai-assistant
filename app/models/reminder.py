from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.timestamps import TimestampMixin
from app.models.enums import TaskStatus
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from app.models.user import User
from datetime import datetime
from typing import Optional
from sqlalchemy.dialects.postgresql import JSONB

class Reminder(Base, TimestampMixin):
    """
    A scheduled reminder for a task to a specific user (WhatsApp only in this PoC).
    Your AI/worker can scan for due reminders and push them through your WhatsApp provider.
    """
    __tablename__ = "reminders"
    __table_args__ = (
        Index("ix_reminders_due_unsent", "due_at", "sent_at"),
        Index("ix_reminders_task_user", "task_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # when to send
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    # when actually sent (null = not yet)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # allow templated payloads / personalization
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # relationships
    user: Mapped["User"] = relationship()