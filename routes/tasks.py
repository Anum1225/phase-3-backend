"""
Task management API routes.

This module provides RESTful endpoints for task CRUD operations:
- POST /api/{user_id}/tasks - Create a new task
- GET /api/{user_id}/tasks - List all tasks with optional filters
- GET /api/{user_id}/tasks/{task_id} - Get a single task by ID
- PUT /api/{user_id}/tasks/{task_id} - Update a task
- DELETE /api/{user_id}/tasks/{task_id} - Delete a task
- PATCH /api/{user_id}/tasks/{task_id}/complete - Toggle task completion

All endpoints enforce user isolation - users can only access their own tasks.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
import logging
from sqlmodel import Session, select, case

from db import get_session
from middleware.jwt import get_current_user_id
from models import Task, TaskPriority, TaskCategory
from schemas.tasks import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter()


def verify_user_access(user_id: str, current_user_id: str) -> None:
    """
    Verify that the user_id in the path matches the authenticated user.

    This function enforces user isolation by ensuring users can only
    access their own resources.

    Args:
        user_id: User ID from the URL path
        current_user_id: User ID from the JWT token

    Raises:
        HTTPException 403: If user_id does not match current_user_id

    Example:
        verify_user_access(user_id="123", current_user_id="456")
        # Raises HTTPException 403
    """
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's tasks",
        )


@router.post("/{user_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    user_id: str,
    task_data: TaskCreate,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Create a new task for the authenticated user.

    Args:
        user_id: User ID from URL path
        task_data: Task creation data (title, description, priority, category)
        session: Database session (injected)
        current_user_id: Authenticated user ID from JWT token (injected)

    Returns:
        TaskResponse: Created task with all fields including generated ID

    Raises:
        HTTPException 403: If user_id does not match authenticated user
        HTTPException 422: If validation fails (invalid data)

    Example:
        POST /api/550e8400-e29b-41d4-a716-446655440000/tasks
        {
            "title": "Complete project proposal",
            "description": "Draft and submit Q1 proposal",
            "priority": "high",
            "category": "work"
        }

        Response: 201 Created
        {
            "id": 1,
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Complete project proposal",
            "description": "Draft and submit Q1 proposal",
            "completed": false,
            "priority": "high",
            "category": "work",
            "created_at": "2025-12-12T10:30:00Z",
            "updated_at": "2025-12-12T10:30:00Z"
        }
    """
    # Verify user isolation
    verify_user_access(user_id, current_user_id)

    # Create task instance
    task = Task(
        user_id=user_id,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        category=task_data.category,
        due_date=task_data.due_date,
        is_recurring=task_data.is_recurring,
        recurring_interval=task_data.recurring_interval,
        reminder_at=task_data.reminder_at,
        position=task_data.position,
    )

    # Persist to database
    session.add(task)
    session.commit()
    session.refresh(task)

    return task


@router.get("/{user_id}/tasks", response_model=List[TaskResponse])
def get_tasks(
    user_id: str,
    # US2: Priority filtering
    priority: Optional[TaskPriority] = Query(
        None, description="Filter by priority (high, medium, low, none)"
    ),
    # US3: Category filtering
    category: Optional[TaskCategory] = Query(
        None, description="Filter by category (work, home, personal, health, finance, shopping, other)"
    ),
    # US4: Search functionality
    search: Optional[str] = Query(
        None, max_length=200, description="Search in title and description (case-insensitive)"
    ),
    # US5: Status filtering
    status: Optional[str] = Query(
        None, regex="^(all|pending|completed)$", description="Filter by status (all, pending, completed)"
    ),
    # US6: Flexible sorting
    sort_by: Optional[str] = Query(
        None, description="Sort by field (priority, created_at, updated_at, title, status, position)"
    ),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order (asc, desc)"),
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Get all tasks for the authenticated user with comprehensive filtering and sorting.

    Supports User Stories 1-6:
    - US1: Basic task listing
    - US2: Priority filtering and sorting
    - US3: Category filtering
    - US4: Search in title/description
    - US5: Multi-criteria filtering (status + priority + category)
    - US6: Flexible sorting by multiple fields

    Args:
        user_id: User ID from URL path
        priority: Optional priority filter (high, medium, low, none)
        category: Optional category filter (work, personal, shopping, health, other)
        search: Optional search query (searches title and description, case-insensitive)
        status: Optional status filter (all, pending, completed)
        sort_by: Optional sort field (priority, created_at, updated_at, title, status)
        order: Sort order (asc, desc) - defaults to desc
        session: Database session (injected)
        current_user_id: Authenticated user ID from JWT token (injected)

    Returns:
        List[TaskResponse]: List of user's tasks matching all filters and sort order

    Raises:
        HTTPException 403: If user_id does not match authenticated user
        HTTPException 400: If invalid query parameters

    Examples:
        GET /api/{user_id}/tasks
        GET /api/{user_id}/tasks?priority=high
        GET /api/{user_id}/tasks?category=work
        GET /api/{user_id}/tasks?search=meeting
        GET /api/{user_id}/tasks?status=pending
        GET /api/{user_id}/tasks?status=pending&priority=high&category=work
        GET /api/{user_id}/tasks?search=proposal&sort_by=priority&order=desc
    """
    # Verify user isolation
    verify_user_access(user_id, current_user_id)

    # Build base query
    statement = select(Task).where(Task.user_id == user_id)

    # Apply priority filter (User Story 2: T033-T034)
    if priority is not None:
        statement = statement.where(Task.priority == priority)

    # Apply category filter
    if category is not None:
        statement = statement.where(Task.category == category)

    # Apply status filter (User Story 5: T067-T068)
    if status and status != "all":
        if status == "pending":
            statement = statement.where(Task.completed == False)
        elif status == "completed":
            statement = statement.where(Task.completed == True)

    # Apply search filter (User Story 4: T054-T057)
    if search:
        # Case-insensitive search in title OR description using PostgreSQL ILIKE
        search_pattern = f"%{search}%"
        from sqlmodel import or_
        statement = statement.where(
            or_(
                Task.title.ilike(search_pattern),
                Task.description.ilike(search_pattern),
            )
        )

    # Apply sorting (User Story 2: T035 for priority, User Story 6: T078-T082 for others)
    if sort_by:
        if sort_by == "priority":
            # Custom priority order: high > medium > low > none (User Story 2: T035)
            priority_order = case(
                (Task.priority == TaskPriority.HIGH, 1),
                (Task.priority == TaskPriority.MEDIUM, 2),
                (Task.priority == TaskPriority.LOW, 3),
                (Task.priority == TaskPriority.NONE, 4),
                else_=5,
            )
            if order == "asc":
                statement = statement.order_by(priority_order.asc())
            else:
                statement = statement.order_by(priority_order.desc())
        elif sort_by == "created_at":
            statement = statement.order_by(
                Task.created_at.asc() if order == "asc" else Task.created_at.desc()
            )
        elif sort_by == "updated_at":
            statement = statement.order_by(
                Task.updated_at.asc() if order == "asc" else Task.updated_at.desc()
            )
        elif sort_by == "title":
            statement = statement.order_by(
                Task.title.asc() if order == "asc" else Task.title.desc()
            )
        elif sort_by == "status":
            statement = statement.order_by(
                Task.completed.asc() if order == "asc" else Task.completed.desc()
            )
        elif sort_by == "position":
            statement = statement.order_by(
                Task.position.asc() if order == "asc" else Task.position.desc()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by field: {sort_by}. "
                f"Valid options: priority, created_at, updated_at, title, status, position",
            )
    else:
        # Default sorting: position ASC (for Kanban) then newest first
        statement = statement.order_by(Task.position.asc(), Task.created_at.desc())

    # Execute query
    tasks = session.exec(statement).all()

    return tasks


@router.get("/{user_id}/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    user_id: str,
    task_id: int,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Get a single task by ID.

    Args:
        user_id: User ID from URL path
        task_id: Task ID to retrieve
        session: Database session (injected)
        current_user_id: Authenticated user ID from JWT token (injected)

    Returns:
        TaskResponse: Task details

    Raises:
        HTTPException 403: If user_id does not match authenticated user
        HTTPException 404: If task does not exist or belongs to another user

    Example:
        GET /api/550e8400-e29b-41d4-a716-446655440000/tasks/1

        Response: 200 OK
        {
            "id": 1,
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Complete project proposal",
            "completed": false,
            ...
        }
    """
    # Verify user isolation
    verify_user_access(user_id, current_user_id)

    # Get task by ID
    task = session.get(Task, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Verify task belongs to user
    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this task",
        )

    return task


@router.put("/{user_id}/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    user_id: str,
    task_id: int,
    task_data: TaskUpdate,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Update a task's fields (partial update supported).

    Only provided fields are updated. Other fields remain unchanged.

    Args:
        user_id: User ID from URL path
        task_id: Task ID to update
        task_data: Fields to update (all optional)
        session: Database session (injected)
        current_user_id: Authenticated user ID from JWT token (injected)

    Returns:
        TaskResponse: Updated task with new values

    Raises:
        HTTPException 403: If user_id does not match authenticated user
        HTTPException 404: If task does not exist
        HTTPException 422: If validation fails

    Example:
        PUT /api/550e8400-e29b-41d4-a716-446655440000/tasks/1
        {
            "priority": "medium",
            "completed": true
        }

        Response: 200 OK
        {
            "id": 1,
            "priority": "medium",
            "completed": true,
            "updated_at": "2025-12-12T11:00:00Z",
            ...
        }
    """
    # Verify user isolation
    verify_user_access(user_id, current_user_id)

    # Get task
    task = session.get(Task, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Verify task belongs to user
    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task",
        )

    # Update fields (only if provided)
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.completed is not None:
        task.completed = task_data.completed
    if task_data.priority is not None:
        task.priority = task_data.priority
    if task_data.category is not None:
        task.category = task_data.category
    if task_data.due_date is not None:
        task.due_date = task_data.due_date
    if task_data.is_recurring is not None:
        task.is_recurring = task_data.is_recurring
    if task_data.recurring_interval is not None:
        task.recurring_interval = task_data.recurring_interval
    if task_data.reminder_at is not None:
        task.reminder_at = task_data.reminder_at
    if task_data.position is not None:
        task.position = task_data.position

    # Update timestamp
    task.updated_at = datetime.utcnow()

    # Persist changes
    session.add(task)
    session.commit()
    session.refresh(task)

    return task


@router.delete("/{user_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    user_id: str,
    task_id: int,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Delete a task.

    Args:
        user_id: User ID from URL path
        task_id: Task ID to delete
        session: Database session (injected)
        current_user_id: Authenticated user ID from JWT token (injected)

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 403: If user_id does not match authenticated user
        HTTPException 404: If task does not exist

    Example:
        DELETE /api/550e8400-e29b-41d4-a716-446655440000/tasks/1

        Response: 204 No Content
    """
    # Verify user isolation
    verify_user_access(user_id, current_user_id)

    # Get task
    task = session.get(Task, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Verify task belongs to user
    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this task",
        )

    # Delete task
    session.delete(task)
    session.commit()

    return None


@router.patch("/{user_id}/tasks/{task_id}/complete", response_model=TaskResponse)
def toggle_task_completion(
    user_id: str,
    task_id: int,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Toggle task completion status (completed <-> pending).

    Convenience endpoint for marking tasks complete/incomplete without
    needing to know the current state.

    Args:
        user_id: User ID from URL path
        task_id: Task ID to toggle
        session: Database session (injected)
        current_user_id: Authenticated user ID from JWT token (injected)

    Returns:
        TaskResponse: Updated task with toggled completion status

    Raises:
        HTTPException 403: If user_id does not match authenticated user
        HTTPException 404: If task does not exist

    Example:
        PATCH /api/550e8400-e29b-41d4-a716-446655440000/tasks/1/complete

        Response: 200 OK
        {
            "id": 1,
            "completed": true,  # Toggled from false to true
            "updated_at": "2025-12-12T11:15:00Z",
            ...
        }
    """
    # Verify user isolation
    verify_user_access(user_id, current_user_id)

    # Get task
    task = session.get(Task, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Verify task belongs to user
    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task",
        )

    # Toggle completion
    task.completed = not task.completed
    task.updated_at = datetime.utcnow()

    # Persist changes
    session.add(task)
    session.commit()
    session.refresh(task)

    return task
