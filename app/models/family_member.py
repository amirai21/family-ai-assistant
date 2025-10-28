from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.timestamps import TimestampMixin
from app.models.enums import MemberRole
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from app.models.family import Family
from app.models.user import User

class FamilyMember(Base, TimestampMixin):
    """
    User scoped to a family with a role (parent/child/caregiver).
    """
    __tablename__ = "family_members"
    __table_args__ = (
        UniqueConstraint("family_id", "user_id", name="uq_family_user"),
        Index("ix_family_members_family_role", "family_id", "role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[MemberRole] = mapped_column(PgEnum(MemberRole, name="member_role"), nullable=False)

    family: Mapped["Family"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship()