from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.family import Family as FamilyModel
from app.api.schemas import FamilyCreate, FamilyUpdate

async def get_families(db: AsyncSession) -> List[FamilyModel]:
    """Get all families"""
    result = await db.execute(select(FamilyModel))
    return list(result.scalars().all())

async def get_family_by_id(db: AsyncSession, family_id: int) -> Optional[FamilyModel]:
    """Get a family by ID"""
    result = await db.execute(select(FamilyModel).where(FamilyModel.id == family_id))
    return result.scalar_one_or_none()

async def get_family_with_members(db: AsyncSession, family_id: int) -> Optional[FamilyModel]:
    """Get a family by ID with all members loaded"""
    result = await db.execute(
        select(FamilyModel)
        .where(FamilyModel.id == family_id)
        .options(selectinload(FamilyModel.memberships).selectinload("user"))
    )
    return result.scalar_one_or_none()

async def create_family(db: AsyncSession, family_data: FamilyCreate) -> FamilyModel:
    """Create a new family"""
    family = FamilyModel(
        name=family_data.name,
    )
    db.add(family)
    await db.flush()
    await db.refresh(family)
    return family

async def update_family(db: AsyncSession, family_id: int, family_data: FamilyUpdate) -> Optional[FamilyModel]:
    """Update an existing family"""
    family = await get_family_by_id(db, family_id)
    if not family:
        return None
    
    if family_data.name is not None:
        family.name = family_data.name
    
    await db.flush()
    await db.refresh(family)
    return family

async def delete_family(db: AsyncSession, family_id: int) -> bool:
    """Delete a family (will cascade delete all members)"""
    family = await get_family_by_id(db, family_id)
    if not family:
        return False
    
    await db.delete(family)
    await db.flush()
    return True


