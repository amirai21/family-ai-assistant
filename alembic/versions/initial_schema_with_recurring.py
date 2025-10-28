"""initial schema with recurring patterns

Revision ID: initial_schema_with_recurring
Revises: 
Create Date: 2025-10-27 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'initial_schema_with_recurring'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create all tables including recurring patterns."""
    
    # Drop existing enums if they exist (CASCADE will drop dependent objects)
    # SQLAlchemy will auto-create them when creating tables
    op.execute("DROP TYPE IF EXISTS recurrence_frequency CASCADE")
    op.execute("DROP TYPE IF EXISTS task_status CASCADE") 
    op.execute("DROP TYPE IF EXISTS member_role CASCADE")
    
    # Create families table
    op.create_table('families',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_families_created_at'), 'families', ['created_at'], unique=False)
    
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('phone_e164', sa.String(length=32), nullable=False),
        sa.Column('whatsapp_opt_in', sa.Boolean(), nullable=False),
        sa.Column('whatsapp_verified', sa.Boolean(), nullable=False),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_e164', name='uq_users_phone')
    )
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)
    op.create_index(op.f('ix_users_phone_e164'), 'users', ['phone_e164'], unique=False)
    
    # Create family_members table
    op.create_table('family_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', postgresql.ENUM('parent', 'child', 'caregiver', name='member_role'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['families.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('family_id', 'user_id', name='uq_family_user')
    )
    op.create_index(op.f('ix_family_members_created_at'), 'family_members', ['created_at'], unique=False)
    op.create_index(op.f('ix_family_members_family_id'), 'family_members', ['family_id'], unique=False)
    op.create_index('ix_family_members_family_role', 'family_members', ['family_id', 'role'], unique=False)
    op.create_index(op.f('ix_family_members_user_id'), 'family_members', ['user_id'], unique=False)
    
    # Create recurring_patterns table
    op.create_table('recurring_patterns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('frequency', postgresql.ENUM('daily', 'weekly', 'monthly', 'yearly', name='recurrence_frequency'), nullable=False),
        sa.Column('interval', sa.Integer(), nullable=False),
        sa.Column('by_day', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('start_time_hour', sa.Integer(), nullable=True),
        sa.Column('start_time_minute', sa.Integer(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('default_assignee_user_id', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_generated_until', sa.DateTime(), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['default_assignee_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['family_id'], ['families.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurring_patterns_created_at'), 'recurring_patterns', ['created_at'], unique=False)
    op.create_index(op.f('ix_recurring_patterns_family_id'), 'recurring_patterns', ['family_id'], unique=False)
    op.create_index('ix_recurring_patterns_family_active', 'recurring_patterns', ['family_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_recurring_patterns_is_active'), 'recurring_patterns', ['is_active'], unique=False)
    
    # Create tasks table (with recurring pattern support)
    op.create_table('tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=False),
        sa.Column('recurring_pattern_id', sa.Integer(), nullable=True),
        sa.Column('occurrence_date', sa.Date(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('assignee_user_id', sa.Integer(), nullable=True),
        sa.Column('status', postgresql.ENUM('todo', 'in_progress', 'done', 'canceled', name='task_status'), nullable=False),
        sa.Column('due_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assignee_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['family_id'], ['families.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recurring_pattern_id'], ['recurring_patterns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_assignee_user_id'), 'tasks', ['assignee_user_id'], unique=False)
    op.create_index(op.f('ix_tasks_created_at'), 'tasks', ['created_at'], unique=False)
    op.create_index(op.f('ix_tasks_due_at'), 'tasks', ['due_at'], unique=False)
    op.create_index(op.f('ix_tasks_family_id'), 'tasks', ['family_id'], unique=False)
    op.create_index('ix_tasks_family_status_due', 'tasks', ['family_id', 'status', 'due_at'], unique=False)
    op.create_index('ix_tasks_recurring_pattern', 'tasks', ['recurring_pattern_id', 'occurrence_date'], unique=False)
    op.create_index(op.f('ix_tasks_recurring_pattern_id'), 'tasks', ['recurring_pattern_id'], unique=False)
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'], unique=False)
    
    # Create reminders table
    op.create_table('reminders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('due_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reminders_created_at'), 'reminders', ['created_at'], unique=False)
    op.create_index(op.f('ix_reminders_due_at'), 'reminders', ['due_at'], unique=False)
    op.create_index('ix_reminders_due_unsent', 'reminders', ['due_at', 'sent_at'], unique=False)
    op.create_index(op.f('ix_reminders_task_id'), 'reminders', ['task_id'], unique=False)
    op.create_index('ix_reminders_task_user', 'reminders', ['task_id', 'user_id'], unique=False)
    op.create_index(op.f('ix_reminders_user_id'), 'reminders', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Drop all tables."""
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index(op.f('ix_reminders_user_id'), table_name='reminders')
    op.drop_index('ix_reminders_task_user', table_name='reminders')
    op.drop_index(op.f('ix_reminders_task_id'), table_name='reminders')
    op.drop_index('ix_reminders_due_unsent', table_name='reminders')
    op.drop_index(op.f('ix_reminders_due_at'), table_name='reminders')
    op.drop_index(op.f('ix_reminders_created_at'), table_name='reminders')
    op.drop_table('reminders')
    
    op.drop_index(op.f('ix_tasks_status'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_recurring_pattern_id'), table_name='tasks')
    op.drop_index('ix_tasks_recurring_pattern', table_name='tasks')
    op.drop_index('ix_tasks_family_status_due', table_name='tasks')
    op.drop_index(op.f('ix_tasks_family_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_due_at'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_created_at'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_assignee_user_id'), table_name='tasks')
    op.drop_table('tasks')
    
    op.drop_index(op.f('ix_recurring_patterns_is_active'), table_name='recurring_patterns')
    op.drop_index('ix_recurring_patterns_family_active', table_name='recurring_patterns')
    op.drop_index(op.f('ix_recurring_patterns_family_id'), table_name='recurring_patterns')
    op.drop_index(op.f('ix_recurring_patterns_created_at'), table_name='recurring_patterns')
    op.drop_table('recurring_patterns')
    
    op.drop_index(op.f('ix_family_members_user_id'), table_name='family_members')
    op.drop_index('ix_family_members_family_role', table_name='family_members')
    op.drop_index(op.f('ix_family_members_family_id'), table_name='family_members')
    op.drop_index(op.f('ix_family_members_created_at'), table_name='family_members')
    op.drop_table('family_members')
    
    op.drop_index(op.f('ix_users_phone_e164'), table_name='users')
    op.drop_index(op.f('ix_users_created_at'), table_name='users')
    op.drop_table('users')
    
    op.drop_index(op.f('ix_families_created_at'), table_name='families')
    op.drop_table('families')
    
    # Drop enums
    op.execute("DROP TYPE recurrence_frequency")
    op.execute("DROP TYPE task_status")
    op.execute("DROP TYPE member_role")

