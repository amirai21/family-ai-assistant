from typing import Dict, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool = True

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1, max_length=100)

class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, min_length=1, max_length=100)
    is_active: bool | None = None

# Mock database
mock_users_db: Dict[int, User] = {
    1: User(id=1, name="Alice Smith", email="alice@example.com", is_active=True),
    2: User(id=2, name="Bob Jones", email="bob@example.com", is_active=True),
}
next_user_id = 3

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=List[User])
async def get_users() -> List[User]:
    """Get all users"""
    return list(mock_users_db.values())

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int) -> User:
    """Get a specific user by ID"""
    if user_id not in mock_users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return mock_users_db[user_id]

@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate) -> User:
    """Create a new user"""
    global next_user_id
    
    new_user = User(
        id=next_user_id,
        name=user_data.name,
        email=user_data.email,
        is_active=True
    )
    mock_users_db[next_user_id] = new_user
    next_user_id += 1
    
    return new_user

@router.put("/{user_id}", response_model=User)
async def update_user(user_id: int, user_data: UserUpdate) -> User:
    """Update an existing user"""
    if user_id not in mock_users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    user = mock_users_db[user_id]
    
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    mock_users_db[user_id] = user
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int) -> None:
    """Delete a user"""
    if user_id not in mock_users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    del mock_users_db[user_id]

