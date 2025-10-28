from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User as UserModel
from app.api.schemas import UserCreate, UserUpdate

async def get_users(db: AsyncSession) -> List[UserModel]:
    """Get all users"""
    result = await db.execute(select(UserModel))
    return list(result.scalars().all())

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[UserModel]:
    """Get a user by ID"""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_phone(db: AsyncSession, phone_e164: str) -> Optional[UserModel]:
    """Get a user by phone number (E.164 format)"""
    result = await db.execute(select(UserModel).where(UserModel.phone_e164 == phone_e164))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_data: UserCreate) -> UserModel:
    """Create a new user"""
    user = UserModel(
        display_name=user_data.display_name,
        phone_e164=user_data.phone_e164,
        whatsapp_opt_in=user_data.whatsapp_opt_in,
        whatsapp_verified=False,
        preferences=user_data.preferences or {},
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate) -> Optional[UserModel]:
    """Update an existing user"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    if user_data.display_name is not None:
        user.display_name = user_data.display_name
    if user_data.phone_e164 is not None:
        user.phone_e164 = user_data.phone_e164
    if user_data.whatsapp_opt_in is not None:
        user.whatsapp_opt_in = user_data.whatsapp_opt_in
    if user_data.whatsapp_verified is not None:
        user.whatsapp_verified = user_data.whatsapp_verified
    if user_data.preferences is not None:
        user.preferences = user_data.preferences
    
    await db.flush()
    await db.refresh(user)
    return user

async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete a user"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.flush()
    return True

async def verify_whatsapp(db: AsyncSession, user_id: int) -> Optional[UserModel]:
    """Mark user's WhatsApp as verified"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    user.whatsapp_verified = True
    await db.flush()
    await db.refresh(user)
    return user

async def toggle_whatsapp_opt_in(db: AsyncSession, user_id: int, opt_in: bool) -> Optional[UserModel]:
    """Toggle user's WhatsApp opt-in status"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    user.whatsapp_opt_in = opt_in
    await db.flush()
    await db.refresh(user)
    return user
