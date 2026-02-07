"""
SQLModel database models.

This module defines database models using SQLModel (SQLAlchemy + Pydantic).
All models with table=True are automatically registered and created on startup.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class TaskPriority(str, Enum):
    """Task priority levels for organizing workload."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class TaskCategory(str, Enum):
    """Task categories for organizing by life domain."""

    WORK = "work"
    HOME = "home"
    PERSONAL = "personal"
    HEALTH = "health"
    FINANCE = "finance"
    SHOPPING = "shopping"
    OTHER = "other"


class User(SQLModel, table=True):
    """
    User authentication model.

    Stores user accounts with hashed passwords for secure authentication.
    Email serves as unique login identifier.

    Security Features:
    - UUID primary key (better distribution than auto-increment)
    - Email unique constraint and index (fast login lookups)
    - Password hash storage only (never plaintext)
    - Timestamps for audit trail
    - Account status flag for soft deletion

    Attributes:
        id: UUID v4, unique user identifier
        email: User's email address (login identifier)
        name: User's display name
        password_hash: Bcrypt hashed password (60 chars, never plaintext)
        created_at: Account creation timestamp (UTC)
        updated_at: Last profile update timestamp (UTC)
        is_active: Account status flag (for soft deletion)
    """

    __tablename__ = "user"

    # Identification
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
        description="Unique user identifier (UUID v4)",
    )

    email: str = Field(
        unique=True,
        index=True,
        max_length=255,
        description="User's email address (login identifier)",
    )

    name: str = Field(max_length=100, description="User's display name")

    # Authentication
    password_hash: str = Field(
        max_length=255,
        description="Bcrypt hashed password (never store plaintext)",
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Account creation timestamp (UTC)",
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp (UTC)",
    )

    is_active: bool = Field(default=True, description="Account active status")

    class Config:
        """Pydantic configuration for JSON serialization"""

        json_encoders = {datetime: lambda v: v.isoformat()}


class Task(SQLModel, table=True):
    """
    Task model with intermediate features (priorities, categories).

    Relationships:
    - Belongs to one User (via user_id foreign key)

    Indexes:
    - user_id: For user isolation and performance
    - completed: For status filtering
    - priority: For priority filtering and sorting
    - category: For category filtering
    - created_at: For date-based sorting

    Attributes:
        id: Unique task identifier (auto-increment)
        user_id: Owner user ID (UUID) - foreign key to User.id
        title: Task title (required, 1-200 characters)
        description: Task description (optional, max 1000 characters)
        completed: Task completion status (default: False)
        priority: Task priority level (default: TaskPriority.NONE)
        category: Task category (default: TaskCategory.OTHER)
        due_date: Task due date (optional)
        is_recurring: Whether the task repeats (default: False)
        recurring_interval: Repetition interval (daily, weekly, etc.)
        reminder_at: Reminder timestamp
        created_at: Task creation timestamp (UTC)
        updated_at: Last update timestamp (UTC)
        position: Task position for Kanban reordering
    """

    __tablename__ = "task"

    # Primary Key
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="Unique task identifier",
    )

    # Foreign Key - User Relationship
    user_id: str = Field(
        foreign_key="user.id",
        index=True,
        description="Owner user ID (UUID)",
    )

    # Core Task Data
    title: str = Field(
        max_length=200,
        min_length=1,
        description="Task title (required, 1-200 characters)",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Task description (optional, max 1000 characters)",
    )

    completed: bool = Field(
        default=False,
        index=True,
        description="Task completion status",
    )

    # Intermediate Features (Phase II)
    priority: TaskPriority = Field(
        default=TaskPriority.NONE,
        index=True,
        description="Task priority level (high, medium, low, none)",
    )

    category: TaskCategory = Field(
        default=TaskCategory.OTHER,
        index=True,
        description="Task category (work, personal, shopping, health, other)",
    )

    # New Fields for Enhanced UI
    due_date: Optional[datetime] = Field(
        default=None,
        description="Task due date",
    )

    is_recurring: bool = Field(
        default=False,
        description="Whether the task repeats",
    )

    recurring_interval: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Repetition interval (e.g., daily, weekly)",
    )

    reminder_at: Optional[datetime] = Field(
        default=None,
        description="Reminder timestamp",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
        description="Task creation timestamp (UTC)",
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp (UTC)",
    )

    position: float = Field(
        default=0.0,
        index=True,
        description="Task position for Kanban reordering",
    )

    class Config:
        """Pydantic configuration for JSON serialization"""

        json_encoders = {datetime: lambda v: v.isoformat()}
