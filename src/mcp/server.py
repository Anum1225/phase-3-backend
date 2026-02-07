"""
FastMCP server for Phase 3 chatbot task management.

This module implements an MCP server with 5 tools for task CRUD operations:
- add_task: Create a new task
- list_tasks: Retrieve user's tasks
- complete_task: Mark a task as complete/incomplete
- delete_task: Delete a task
- update_task: Update task details

The server uses stateless HTTP transport and integrates with the database
via lifespan context management.
"""

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
from sqlmodel import Session, create_engine, select

from models import Task, TaskCategory, TaskPriority

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create database engine
engine = create_engine(DATABASE_URL)


@dataclass
class AppContext:
    """Application context with database session."""

    engine: any


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """
    Lifespan context manager for MCP server.

    Provides database engine to all MCP tools via context.
    """
    yield AppContext(engine=engine)


# Initialize FastMCP server with stateless HTTP
mcp = FastMCP(
    "Todo Task Manager",
    stateless_http=True,
    json_response=True,
    lifespan=app_lifespan,
)


def get_session(ctx: Context) -> Session:
    """
    Get database session from context.

    Args:
        ctx: MCP context with lifespan_context

    Returns:
        SQLModel database session
    """
    print(f"[DEBUG] get_session called, ctx type: {type(ctx)}")
    print(f"[DEBUG] ctx.request_context: {hasattr(ctx, 'request_context')}")

    try:
        app_ctx = ctx.request_context.lifespan_context
        print(f"[DEBUG] app_ctx retrieved: {type(app_ctx)}")
        print(f"[DEBUG] app_ctx.engine: {hasattr(app_ctx, 'engine')}")

        session = Session(app_ctx.engine)
        print(f"[DEBUG] Session created successfully")
        return session
    except Exception as e:
        print(f"[DEBUG] ERROR in get_session: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@mcp.tool()
def add_task(
    user_id: str,
    title: str,
    description: str = None,
    priority: str = "none",
    category: str = "other",
    due_date: str = None,
    is_recurring: bool = False,
    recurring_interval: str = None,
    *,
    ctx: Context,
) -> dict:
    """
    Add a new task to the user's todo list.

    Args:
        user_id: ID of the user creating the task (UUID)
        title: Task title (required, 1-200 characters)
        description: Optional task description (max 1000 characters)
        priority: Task priority - one of: high, medium, low, none (default: none)
        category: Task category - one of: work, personal, shopping, health, other (default: other)
        due_date: Optional ISO format date string (YYYY-MM-DDTHH:MM:SS)
        is_recurring: Whether the task repeats (default: false)
        recurring_interval: Repetition interval (e.g., daily, weekly, monthly) (default: None)

    Returns:
        dict: Created task with id, title, description, priority, category, completed, created_at

    Example:
        add_task("user123", "Buy groceries", "Milk, eggs, bread", priority="medium", category="shopping")
    """
    print(f"\n{'='*60}")
    print(f"[DEBUG] add_task CALLED")
    print(f"[DEBUG] user_id: {user_id}")
    print(f"[DEBUG] title: {title}")
    print(f"[DEBUG] description: {description}")
    print(f"[DEBUG] priority: {priority}")
    print(f"[DEBUG] category: {category}")
    print(f"[DEBUG] ctx: {type(ctx)}")
    print(f"{'='*60}\n")

    print(f"[DEBUG] Calling get_session...")
    session = get_session(ctx)
    print(f"[DEBUG] Got session, continuing...")

    try:
        print(f"[DEBUG] Validating priority: {priority}")
        # Validate priority
        try:
            priority_enum = TaskPriority(priority.lower())
        except ValueError:
            return {
                "error": f"Invalid priority '{priority}'. Must be one of: high, medium, low, none"
            }

        # Validate category
        try:
            category_enum = TaskCategory(category.lower())
        except ValueError:
            return {
                "error": f"Invalid category '{category}'. Must be one of: work, personal, shopping, health, other"
            }

        # Create task
        task = Task(
            user_id=user_id,
            title=title[:200],  # Enforce max length
            description=description[:1000] if description else None,
            priority=priority_enum,
            category=category_enum,
            completed=False,
            due_date=datetime.fromisoformat(due_date.replace('Z', '+00:00')) if due_date else None,
            is_recurring=is_recurring,
            recurring_interval=recurring_interval,
        )

        session.add(task)
        session.commit()
        session.refresh(task)

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority.value,
            "category": task.category.value,
            "completed": task.completed,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "is_recurring": task.is_recurring,
            "recurring_interval": task.recurring_interval,
            "created_at": task.created_at.isoformat(),
        }

    except Exception as e:
        session.rollback()
        return {"error": f"Failed to create task: {str(e)}"}
    finally:
        session.close()


@mcp.tool()
def list_tasks(
    user_id: str,
    status: str = "all",
    priority: str = None,
    category: str = None,
    search: str = None,
    *,
    ctx: Context,
) -> dict:
    """
    List all tasks for a user with optional filtering.

    Args:
        user_id: ID of the user (UUID)
        status: Filter by status - one of: all, pending, completed (default: all)
        priority: Optional filter by priority - one of: high, medium, low, none
        category: Optional filter by category - one of: work, personal, shopping, health, other
        search: Optional search string to filter tasks by title or description

    Returns:
        dict: List of tasks matching filters with count

    Example:
        list_tasks("user123", status="pending", priority="high", search="grocery")
    """
    session = get_session(ctx)

    try:
        # Build query
        query = select(Task).where(Task.user_id == user_id)

        # Apply status filter
        if status == "pending":
            query = query.where(Task.completed == False)
        elif status == "completed":
            query = query.where(Task.completed == True)
        elif status != "all":
            return {
                "error": f"Invalid status '{status}'. Must be one of: all, pending, completed"
            }

        # Apply priority filter
        if priority:
            try:
                priority_enum = TaskPriority(priority.lower())
                query = query.where(Task.priority == priority_enum)
            except ValueError:
                return {
                    "error": f"Invalid priority '{priority}'. Must be one of: high, medium, low, none"
                }

        # Apply category filter
        if category:
            try:
                category_enum = TaskCategory(category.lower())
                query = query.where(Task.category == category_enum)
            except ValueError:
                return {
                    "error": f"Invalid category '{category}'. Must be one of: work, personal, shopping, health, other"
                }

        # Apply search filter (Case-insensitive)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Task.title.ilike(search_pattern)) | (Task.description.ilike(search_pattern))
            )

        # Execute query
        query = query.order_by(Task.created_at.desc())
        tasks = session.exec(query).all()

        return {
            "count": len(tasks),
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "priority": task.priority.value,
                    "category": task.category.value,
                    "completed": task.completed,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                }
                for task in tasks
            ],
        }

    except Exception as e:
        return {"error": f"Failed to retrieve tasks: {str(e)}"}
    finally:
        session.close()


@mcp.tool()
def complete_task(user_id: str, task_id: int, completed: bool = True, *, ctx: Context) -> dict:
    """
    Mark a task as complete or incomplete.

    Args:
        user_id: ID of the user who owns the task (UUID)
        task_id: ID of the task to update
        completed: Set to True to mark complete, False to mark incomplete (default: True)

    Returns:
        dict: Updated task status

    Example:
        complete_task("user123", 42, completed=True)
    """
    session = get_session(ctx)

    try:
        # Get task
        task = session.get(Task, task_id)

        if not task:
            return {"error": f"Task with id {task_id} not found"}

        # Verify ownership
        if task.user_id != user_id:
            return {"error": "Not authorized to update this task"}

        # Update completion status
        task.completed = completed
        task.updated_at = datetime.utcnow()

        session.add(task)
        session.commit()
        session.refresh(task)

        return {
            "id": task.id,
            "title": task.title,
            "completed": task.completed,
            "updated_at": task.updated_at.isoformat(),
        }

    except Exception as e:
        session.rollback()
        return {"error": f"Failed to update task: {str(e)}"}
    finally:
        session.close()


@mcp.tool()
def delete_task(user_id: str, task_id: int, *, ctx: Context) -> dict:
    """
    Delete a task from the user's todo list.

    Args:
        user_id: ID of the user who owns the task (UUID)
        task_id: ID of the task to delete

    Returns:
        dict: Confirmation of deletion

    Example:
        delete_task("user123", 42)
    """
    session = get_session(ctx)

    try:
        # Get task
        task = session.get(Task, task_id)

        if not task:
            return {"error": f"Task with id {task_id} not found"}

        # Verify ownership
        if task.user_id != user_id:
            return {"error": "Not authorized to delete this task"}

        # Delete task
        task_title = task.title
        session.delete(task)
        session.commit()

        return {
            "success": True,
            "message": f"Task '{task_title}' (id: {task_id}) deleted successfully",
        }

    except Exception as e:
        session.rollback()
        return {"error": f"Failed to delete task: {str(e)}"}
    finally:
        session.close()


@mcp.tool()
def update_task(
    user_id: str,
    task_id: int,
    title: str = None,
    description: str = None,
    priority: str = None,
    category: str = None,
    due_date: str = None,
    is_recurring: bool = None,
    recurring_interval: str = None,
    *,
    ctx: Context,
) -> dict:
    """
    Update task details (title, description, priority, or category).

    Args:
        user_id: ID of the user who owns the task (UUID)
        task_id: ID of the task to update
        title: New task title (optional, 1-200 characters)
        description: New task description (optional, max 1000 characters)
        priority: New priority - one of: high, medium, low, none (optional)
        category: New category - one of: work, personal, shopping, health, other (optional)
        due_date: New due date string (optional)
        is_recurring: New recurring status (optional)
        recurring_interval: New interval (optional)

    Returns:
        dict: Updated task details

    Example:
        update_task("user123", 42, title="Buy groceries and cook", priority="high")
    """
    session = get_session(ctx)

    try:
        # Get task
        task = session.get(Task, task_id)

        if not task:
            return {"error": f"Task with id {task_id} not found"}

        # Verify ownership
        if task.user_id != user_id:
            return {"error": "Not authorized to update this task"}

        # Update fields
        if title is not None:
            task.title = title[:200]  # Enforce max length

        if description is not None:
            task.description = description[:1000] if description else None

        if priority is not None:
            try:
                task.priority = TaskPriority(priority.lower())
            except ValueError:
                return {
                    "error": f"Invalid priority '{priority}'. Must be one of: high, medium, low, none"
                }

        if category is not None:
            try:
                task.category = TaskCategory(category.lower())
            except ValueError:
                return {
                    "error": f"Invalid category '{category}'. Must be one of: work, personal, shopping, health, other"
                }

        if due_date is not None:
            try:
                task.due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00')) if due_date else None
            except ValueError:
                return {"error": f"Invalid date format '{due_date}'. Use ISO format (YYYY-MM-DDTHH:MM:SS)"}

        if is_recurring is not None:
            task.is_recurring = is_recurring

        if recurring_interval is not None:
            task.recurring_interval = recurring_interval

        task.updated_at = datetime.utcnow()

        session.add(task)
        session.commit()
        session.refresh(task)

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority.value,
            "category": task.category.value,
            "completed": task.completed,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "is_recurring": task.is_recurring,
            "recurring_interval": task.recurring_interval,
            "updated_at": task.updated_at.isoformat(),
        }

    except Exception as e:
        session.rollback()
        return {"error": f"Failed to update task: {str(e)}"}
    finally:
        session.close()
