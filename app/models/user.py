from sqlalchemy import String, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint
from app.core.database import Base
from app.models.timestamps import TimestampMixin

class User(Base, TimestampMixin):
    """
    Global user (so a person can be in multiple families if needed).
    For a strict single-family PoC you can drop multi-family and move role to this table.
    """
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("phone_e164", name="uq_users_phone"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # WhatsApp integration: store phone in E.164 format (e.g., +9725XXXXXXX)
    phone_e164: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    whatsapp_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # optional place for prefs (quiet hours, language, etc.)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

