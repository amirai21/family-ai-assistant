from datetime import datetime, date, time
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re
from app.models.enums import MemberRole, TaskStatus, RecurrenceFrequency

class UserBase(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    phone_e164: str = Field(..., min_length=8, max_length=32, description="Phone in E.164 format (e.g., +972512345678)")
    
    @field_validator("phone_e164")
    @classmethod
    def validate_phone_e164(cls, v: str) -> str:
        """Validate E.164 phone format"""
        if not re.match(r'^\+[1-9]\d{1,14}$', v):
            raise ValueError("Phone must be in E.164 format (e.g., +972512345678)")
        return v

class UserCreate(UserBase):
    whatsapp_opt_in: bool = True
    preferences: dict = Field(default_factory=dict)

class UserUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=100)
    phone_e164: str | None = Field(None, min_length=8, max_length=32)
    whatsapp_opt_in: bool | None = None
    whatsapp_verified: bool | None = None
    preferences: dict | None = None
    
    @field_validator("phone_e164")
    @classmethod
    def validate_phone_e164(cls, v: str | None) -> str | None:
        """Validate E.164 phone format"""
        if v is not None and not re.match(r'^\+[1-9]\d{1,14}$', v):
            raise ValueError("Phone must be in E.164 format (e.g., +972512345678)")
        return v

class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    whatsapp_opt_in: bool
    whatsapp_verified: bool
    preferences: dict
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Family Schemas
# ============================================================================

class FamilyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)

class FamilyCreate(FamilyBase):
    pass

class FamilyUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)

class Family(FamilyBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


# ============================================================================
# FamilyMember Schemas
# ============================================================================

class FamilyMemberBase(BaseModel):
    family_id: int
    user_id: int
    role: MemberRole

class FamilyMemberCreate(BaseModel):
    user_id: int
    role: MemberRole

class FamilyMemberUpdate(BaseModel):
    role: MemberRole | None = None

class FamilyMember(FamilyMemberBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime

class FamilyMemberWithUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    family_id: int
    user_id: int
    role: MemberRole
    user: User
    created_at: datetime
    updated_at: datetime

class FamilyWithMembers(Family):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    members: list[FamilyMemberWithUser] = Field(default=[], validation_alias='memberships', serialization_alias='members')


# ============================================================================
# Task Schemas
# ============================================================================

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assignee_user_id: Optional[int] = None
    due_at: Optional[datetime] = None
    meta: dict = Field(default_factory=dict)

class TaskCreate(TaskBase):
    family_id: int
    status: TaskStatus = TaskStatus.todo
    created_by_user_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    assignee_user_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    meta: Optional[dict] = None

class Task(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    family_id: int
    created_by_user_id: Optional[int]
    status: TaskStatus
    completed_at: Optional[datetime]
    recurring_pattern_id: Optional[int] = None
    occurrence_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

class TaskWithDetails(Task):
    created_by: Optional[User] = None
    assignee: Optional[User] = None


# ============================================================================
# Reminder Schemas
# ============================================================================

class ReminderBase(BaseModel):
    task_id: int
    user_id: int
    due_at: datetime
    payload: dict = Field(default_factory=dict)

class ReminderCreate(BaseModel):
    user_id: int
    due_at: datetime
    payload: dict = Field(default_factory=dict)

class ReminderUpdate(BaseModel):
    due_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    payload: Optional[dict] = None

class Reminder(ReminderBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class ReminderWithUser(Reminder):
    user: User


# ============================================================================
# RecurringPattern Schemas
# ============================================================================

class RecurringPatternBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    frequency: RecurrenceFrequency
    interval: int = Field(default=1, ge=1, description="Repeat every N days/weeks/months")
    by_day: Optional[list[int]] = Field(default=None, description="Days of week (0-6) or month (1-31)")
    start_time_hour: Optional[int] = Field(default=None, ge=0, le=23)
    start_time_minute: Optional[int] = Field(default=0, ge=0, le=59)
    duration_minutes: Optional[int] = Field(default=None, ge=1, description="Duration in minutes")
    default_assignee_user_id: Optional[int] = None
    meta: dict = Field(default_factory=dict)

class RecurringPatternCreate(RecurringPatternBase):
    family_id: int
    start_date: datetime
    end_date: Optional[datetime] = None
    created_by_user_id: Optional[int] = None
    is_active: bool = True

class RecurringPatternUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    frequency: Optional[RecurrenceFrequency] = None
    interval: Optional[int] = Field(None, ge=1)
    by_day: Optional[list[int]] = None
    start_time_hour: Optional[int] = Field(None, ge=0, le=23)
    start_time_minute: Optional[int] = Field(None, ge=0, le=59)
    duration_minutes: Optional[int] = Field(None, ge=1)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    default_assignee_user_id: Optional[int] = None
    is_active: Optional[bool] = None
    meta: Optional[dict] = None

class RecurringPattern(RecurringPatternBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    family_id: int
    start_date: datetime
    end_date: Optional[datetime]
    created_by_user_id: Optional[int]
    is_active: bool
    last_generated_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class RecurringPatternWithDetails(RecurringPattern):
    default_assignee: Optional[User] = None
    created_by: Optional[User] = None
