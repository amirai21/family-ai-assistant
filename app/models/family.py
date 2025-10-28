from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.timestamps import TimestampMixin

class Family(Base, TimestampMixin):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # convenience relationships
    memberships: Mapped[list["FamilyMember"]] = relationship(back_populates="family", cascade="all, delete-orphan")