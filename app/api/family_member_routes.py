from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import FamilyMember, FamilyMemberCreate, FamilyMemberUpdate, FamilyMemberWithUser
from app.core.database import get_db
from app.services import family_member_service, family_service, user_service

router = APIRouter(tags=["family-members"])

@router.get("/families/{family_id}/members", response_model=List[FamilyMemberWithUser])
async def get_family_members(
    family_id: int,
    db: AsyncSession = Depends(get_db)
) -> List[FamilyMemberWithUser]:
    """Get all members of a family"""
    # Verify family exists
    family = await family_service.get_family_by_id(db, family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family with id {family_id} not found"
        )
    
    members = await family_member_service.get_family_members(db, family_id)
    return members

@router.get("/users/{user_id}/families", response_model=List[FamilyMember])
async def get_user_families(
    user_id: int,
    db: AsyncSession = Depends(get_db)
) -> List[FamilyMember]:
    """Get all families a user belongs to"""
    # Verify user exists
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    memberships = await family_member_service.get_user_families(db, user_id)
    return memberships

@router.get("/family-members/{member_id}", response_model=FamilyMemberWithUser)
async def get_family_member(
    member_id: int,
    db: AsyncSession = Depends(get_db)
) -> FamilyMemberWithUser:
    """Get a specific family member by ID"""
    member = await family_member_service.get_family_member_by_id(db, member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family member with id {member_id} not found"
        )
    return member

@router.post("/families/{family_id}/members", response_model=FamilyMemberWithUser, status_code=status.HTTP_201_CREATED)
async def add_family_member(
    family_id: int,
    member_data: FamilyMemberCreate,
    db: AsyncSession = Depends(get_db)
) -> FamilyMemberWithUser:
    """Add a user to a family with a specific role"""
    # Verify family exists
    family = await family_service.get_family_by_id(db, family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family with id {family_id} not found"
        )
    
    # Verify user exists
    user = await user_service.get_user_by_id(db, member_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {member_data.user_id} not found"
        )
    
    # Check if user is already a member
    existing_member = await family_member_service.get_family_member_by_user(
        db, family_id, member_data.user_id
    )
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {member_data.user_id} is already a member of family {family_id}"
        )
    
    member = await family_member_service.create_family_member(db, family_id, member_data)
    return member

@router.put("/family-members/{member_id}", response_model=FamilyMemberWithUser)
async def update_family_member(
    member_id: int,
    member_data: FamilyMemberUpdate,
    db: AsyncSession = Depends(get_db)
) -> FamilyMemberWithUser:
    """Update a family member's role"""
    member = await family_member_service.update_family_member(db, member_id, member_data)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family member with id {member_id} not found"
        )
    return member

@router.delete("/family-members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_family_member(
    member_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove a user from a family"""
    deleted = await family_member_service.delete_family_member(db, member_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family member with id {member_id} not found"
        )





