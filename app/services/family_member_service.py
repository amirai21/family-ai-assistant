from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.family_member import FamilyMember as FamilyMemberModel
from app.api.schemas import FamilyMemberCreate, FamilyMemberUpdate


async def get_family_members(db: AsyncSession, family_id: int) -> List[FamilyMemberModel]:
    """Get all members of a family"""
    result = await db.execute(
        select(FamilyMemberModel)
        .where(FamilyMemberModel.family_id == family_id)
        .options(selectinload(FamilyMemberModel.user))
    )
    return list(result.scalars().all())


async def get_user_families(db: AsyncSession, user_id: int) -> List[FamilyMemberModel]:
    """Get all families a user belongs to"""
    result = await db.execute(
        select(FamilyMemberModel)
        .where(FamilyMemberModel.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_family_member_by_id(db: AsyncSession, member_id: int) -> Optional[FamilyMemberModel]:
    """Get a specific family member by ID"""
    result = await db.execute(
        select(FamilyMemberModel)
        .where(FamilyMemberModel.id == member_id)
        .options(selectinload(FamilyMemberModel.user))
    )
    return result.scalar_one_or_none()


async def get_family_member_by_user(
    db: AsyncSession, 
    family_id: int, 
    user_id: int
) -> Optional[FamilyMemberModel]:
    """Check if a user is already a member of a family"""
    result = await db.execute(
        select(FamilyMemberModel).where(
            and_(
                FamilyMemberModel.family_id == family_id,
                FamilyMemberModel.user_id == user_id
            )
        )
    )
    return result.scalar_one_or_none()


async def create_family_member(
    db: AsyncSession,
    family_id: int,
    member_data: FamilyMemberCreate
) -> FamilyMemberModel:
    """Add a user to a family with a specific role"""
    member = FamilyMemberModel(
        family_id=family_id,
        user_id=member_data.user_id,
        role=member_data.role
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    
    # Load relationship
    await db.refresh(member, ["user"])
    return member


async def update_family_member(
    db: AsyncSession,
    member_id: int,
    member_data: FamilyMemberUpdate
) -> Optional[FamilyMemberModel]:
    """Update a family member's role"""
    member = await get_family_member_by_id(db, member_id)
    if not member:
        return None
    
    if member_data.role is not None:
        member.role = member_data.role
    
    await db.flush()
    await db.refresh(member)
    await db.refresh(member, ["user"])
    return member


async def delete_family_member(db: AsyncSession, member_id: int) -> bool:
    """Remove a user from a family"""
    member = await get_family_member_by_id(db, member_id)
    if not member:
        return False
    
    await db.delete(member)
    await db.flush()
    return True

