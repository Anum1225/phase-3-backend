"""
Pydantic schemas for task API requests and responses.

This module defines validation schemas for task operations:
- TaskCreate: Validates data when creating a new task
- TaskUpdate: Validates data when updating an existing task (partial updates)
- TaskResponse: Standardizes task data in API responses

All schemas leverage Pydantic for automatic validation and serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models import TaskCategory, TaskPriority


class TaskCreate(BaseModel):
    """
    Schema for creating a new task.

    All fields except title have sensible defaults.
    Pydantic automatically validates enum values.

    Attributes:
        title: Task title (required, 1-200 characters)
        description: Task description (optional, max 1000 characters)
        priority: Task priority level (optional, defaults to 'none')
        category: Task category (optional, defaults to 'other')
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Task title (required)",
        examples=["Buy groceries"],
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Task description (optional)",
        examples=["Milk, eggs, bread, vegetables"],
    )

    priority: TaskPriority = Field(
        default=TaskPriority.NONE,
        description="Task priority (optional, defaults to 'none')",
        examples=["high"],
    )

    category: TaskCategory = Field(
        default=TaskCategory.OTHER,
        description="Task category (optional, defaults to 'other')",
        examples=["shopping"],
    )

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
        description="Repetition interval",
    )

    reminder_at: Optional[datetime] = Field(
        default=None,
        description="Reminder timestamp",
    )

    position: float = Field(
        default=0.0,
        description="Task position for Kanban reordering",
    )

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "title": "Complete project proposal",
                "description": "Draft and submit Q1 proposal",
                "priority": "high",
                "category": "work",
            }
        }


class TaskUpdate(BaseModel):
    """
    Schema for updating an existing task.

    All fields are optional to support partial updates.
    Only provided fields will be updated in the database.

    Attributes:
        title: Updated task title (optional, 1-200 characters)
        description: Updated task description (optional, max 1000 characters)
        completed: Updated completion status (optional)
        priority: Updated priority level (optional)
        category: Updated category (optional)
    """

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Updated task title",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Updated task description",
    )

    completed: Optional[bool] = Field(
        default=None,
        description="Updated completion status",
    )

    priority: Optional[TaskPriority] = Field(
        default=None,
        description="Updated priority level",
    )

    category: Optional[TaskCategory] = Field(
        default=None,
        description="Updated category",
    )

    due_date: Optional[datetime] = Field(
        default=None,
        description="Updated due date",
    )

    is_recurring: Optional[bool] = Field(
        default=None,
        description="Updated recurring status",
    )

    recurring_interval: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Updated recurring interval",
    )

    reminder_at: Optional[datetime] = Field(
        default=None,
        description="Updated reminder timestamp",
    )

    position: Optional[float] = Field(
        default=None,
        description="Updated task position",
    )

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "priority": "medium",
                "completed": True,
            }
        }


class TaskResponse(BaseModel):
    """
    Schema for task in API responses.

    This schema is used for all task responses (create, read, update).
    Automatically serializes SQLModel Task objects to JSON.

    Attributes:
        id: Unique task identifier
        user_id: Owner user ID (UUID)
        title: Task title
        description: Task description (nullable)
        completed: Task completion status
        priority: Task priority level
        category: Task category
        created_at: Task creation timestamp (UTC)
        updated_at: Last update timestamp (UTC)
    """

    id: int
    user_id: str
    title: str
    description: Optional[str]
    completed: bool
    priority: TaskPriority
    category: TaskCategory
    due_date: Optional[datetime]
    is_recurring: bool
    recurring_interval: Optional[str]
    reminder_at: Optional[datetime]
    position: float
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration"""

        from_attributes = True  # Enable ORM mode for SQLModel compatibility
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Complete project proposal",
                "description": "Draft and submit Q1 proposal",
                "completed": False,
                "priority": "high",
                "category": "work",
                "created_at": "2025-12-12T10:30:00Z",
                "updated_at": "2025-12-12T10:30:00Z",
            }
        }
