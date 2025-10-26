from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1, max_length=100)

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, min_length=1, max_length=100)
    is_active: bool | None = None

class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

