from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import User, UserCreate, UserUpdate
from app.core.database import get_db
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=List[User])
async def get_users(db: AsyncSession = Depends(get_db)) -> List[User]:
    """Get all users"""
    users = await user_service.get_users(db)
    return users

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> User:
    """Get a specific user by ID"""
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return user

@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Create a new user"""
    existing_user = await user_service.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {user_data.email} already exists"
        )
    
    user = await user_service.create_user(db, user_data)
    return user

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Update an existing user"""
    user = await user_service.update_user(db, user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a user"""
    deleted = await user_service.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
