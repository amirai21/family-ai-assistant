from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import Family, FamilyCreate, FamilyUpdate, FamilyWithMembers
from app.core.database import get_db
from app.services import family_service

router = APIRouter(prefix="/families", tags=["families"])

@router.get("", response_model=List[Family])
async def get_families(db: AsyncSession = Depends(get_db)) -> List[Family]:
    """Get all families"""
    families = await family_service.get_families(db)
    return families

@router.get("/{family_id}", response_model=Family)
async def get_family(family_id: int, db: AsyncSession = Depends(get_db)) -> Family:
    """Get a specific family by ID"""
    family = await family_service.get_family_by_id(db, family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family with id {family_id} not found"
        )
    return family

@router.get("/{family_id}/with-members", response_model=FamilyWithMembers)
async def get_family_with_members(
    family_id: int,
    db: AsyncSession = Depends(get_db)
) -> FamilyWithMembers:
    """Get a family with all its members"""
    family = await family_service.get_family_with_members(db, family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family with id {family_id} not found"
        )
    return family

@router.post("", response_model=Family, status_code=status.HTTP_201_CREATED)
async def create_family(
    family_data: FamilyCreate,
    db: AsyncSession = Depends(get_db)
) -> Family:
    """Create a new family"""
    family = await family_service.create_family(db, family_data)
    return family

@router.put("/{family_id}", response_model=Family)
async def update_family(
    family_id: int,
    family_data: FamilyUpdate,
    db: AsyncSession = Depends(get_db)
) -> Family:
    """Update an existing family"""
    family = await family_service.update_family(db, family_id, family_data)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family with id {family_id} not found"
        )
    return family

@router.delete("/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family(family_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a family (will also delete all family members)"""
    deleted = await family_service.delete_family(db, family_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family with id {family_id} not found"
        )





