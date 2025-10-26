from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User as UserModel
from app.api.schemas import UserCreate, UserUpdate

async def get_users(db: AsyncSession) -> List[UserModel]:
    result = await db.execute(select(UserModel))
    return list(result.scalars().all())

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[UserModel]:
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[UserModel]:
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_data: UserCreate) -> UserModel:
    user = UserModel(
        name=user_data.name,
        email=user_data.email,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate) -> Optional[UserModel]:
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    await db.flush()
    await db.refresh(user)
    return user

async def delete_user(db: AsyncSession, user_id: int) -> bool:
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.flush()
    return True

