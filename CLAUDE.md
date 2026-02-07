# Backend Guidelines - FastAPI Application

## Overview
This is the backend API for the Todo App built with FastAPI. It provides RESTful endpoints for task management with JWT authentication and persistent storage in Neon PostgreSQL.

## Technology Stack

- **Framework**: FastAPI
- **Language**: Python 3.13+
- **ORM**: SQLModel (built on SQLAlchemy + Pydantic)
- **Database**: Neon Serverless PostgreSQL
- **Authentication**: JWT tokens (shared secret with frontend)
- **Package Manager**: UV
- **Testing**: Pytest
- **Deployment**: Hugging Face Spaces (or alternative Python hosting)

## Project Structure

```
backend/
├── main.py                  # FastAPI application entry point
├── models.py                # SQLModel database models
├── db.py                    # Database connection and session management
├── routes/                  # API route handlers
│   ├── __init__.py
│   ├── auth.py              # Authentication endpoints
│   └── tasks.py             # Task CRUD endpoints
├── middleware/              # Custom middleware
│   ├── __init__.py
│   └── jwt.py               # JWT verification middleware
├── schemas/                 # Pydantic request/response schemas
│   ├── __init__.py
│   ├── auth.py
│   └── tasks.py
├── tests/                   # Unit and integration tests
│   ├── __init__.py
│   ├── test_auth.py
│   └── test_tasks.py
├── .env                     # Environment variables
├── pyproject.toml           # Python dependencies
└── uv.lock                  # Locked dependency versions
```

## Development Patterns

### 1. Application Entry Point
```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, tasks
from db import engine, create_db_and_tables

app = FastAPI(
    title="Todo API",
    description="RESTful API for Todo application",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "https://your-frontend.vercel.app"  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api", tags=["authentication"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
def read_root():
    return {"message": "Todo API is running"}
```

### 2. Database Models with SQLModel
```python
# models.py
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class User(SQLModel, table=True):
    """User model - managed by Better Auth"""
    id: str = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Task(SQLModel, table=True):
    """Task model for todo items"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 3. Database Connection
```python
# db.py
from sqlmodel import create_engine, SQLModel, Session
from typing import Generator
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    """Create database tables on startup"""
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """Dependency for getting database session"""
    with Session(engine) as session:
        yield session
```

### 4. JWT Middleware
```python
# middleware/jwt.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import jwt
import os

security = HTTPBearer()

JWT_SECRET = os.getenv("BETTER_AUTH_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def verify_jwt_token(credentials: HTTPAuthCredentials = Depends(security)) -> dict:
    """Verify JWT token and extract payload"""
    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_current_user_id(token_payload: dict = Depends(verify_jwt_token)) -> str:
    """Extract user_id from verified token"""
    user_id = token_payload.get("sub") or token_payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    return user_id
```

### 5. Request/Response Schemas
```python
# schemas/tasks.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TaskCreate(BaseModel):
    """Schema for creating a new task"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: Optional[bool] = None

class TaskResponse(BaseModel):
    """Schema for task response"""
    id: int
    user_id: str
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### 6. API Routes with User Isolation
```python
# routes/tasks.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from typing import List
from models import Task
from schemas.tasks import TaskCreate, TaskUpdate, TaskResponse
from db import get_session
from middleware.jwt import get_current_user_id

router = APIRouter()

@router.get("/{user_id}/tasks", response_model=List[TaskResponse])
def get_tasks(
    user_id: str,
    status_filter: str = Query("all", regex="^(all|pending|completed)$"),
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get all tasks for authenticated user"""
    # Verify user_id matches authenticated user
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's tasks"
        )

    # Build query
    query = select(Task).where(Task.user_id == user_id)

    if status_filter == "pending":
        query = query.where(Task.completed == False)
    elif status_filter == "completed":
        query = query.where(Task.completed == True)

    tasks = session.exec(query).all()
    return tasks

@router.post("/{user_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    user_id: str,
    task_data: TaskCreate,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id)
):
    """Create a new task for authenticated user"""
    # Verify user_id matches authenticated user
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create tasks for this user"
        )

    # Create task
    task = Task(
        user_id=user_id,
        title=task_data.title,
        description=task_data.description
    )

    session.add(task)
    session.commit()
    session.refresh(task)

    return task

@router.put("/{user_id}/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    user_id: str,
    task_id: int,
    task_data: TaskUpdate,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id)
):
    """Update a task for authenticated user"""
    # Verify user_id matches authenticated user
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's tasks"
        )

    # Get task
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify task belongs to user
    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )

    # Update fields
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.completed is not None:
        task.completed = task_data.completed

    task.updated_at = datetime.utcnow()

    session.add(task)
    session.commit()
    session.refresh(task)

    return task

@router.delete("/{user_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    user_id: str,
    task_id: int,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete a task for authenticated user"""
    # Verify user_id matches authenticated user
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user's tasks"
        )

    # Get task
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify task belongs to user
    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this task"
        )

    session.delete(task)
    session.commit()

    return None

@router.patch("/{user_id}/tasks/{task_id}/complete", response_model=TaskResponse)
def toggle_task_completion(
    user_id: str,
    task_id: int,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id)
):
    """Toggle task completion status"""
    # Verify user_id matches authenticated user
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's tasks"
        )

    # Get task
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify task belongs to user
    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )

    # Toggle completion
    task.completed = not task.completed
    task.updated_at = datetime.utcnow()

    session.add(task)
    session.commit()
    session.refresh(task)

    return task
```

## Environment Variables

Create `.env` in the backend root:

```env
DATABASE_URL=postgresql://user:password@host:5432/database
BETTER_AUTH_SECRET=your-shared-secret-key-here
JWT_ALGORITHM=HS256
```

**Important**:
- `DATABASE_URL`: Neon PostgreSQL connection string
- `BETTER_AUTH_SECRET`: Must match frontend's secret
- Never commit `.env` to version control

## API Conventions

### 1. HTTP Status Codes
- `200 OK`: Successful GET, PUT, PATCH
- `201 Created`: Successful POST
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: User not authorized for resource
- `404 Not Found`: Resource doesn't exist
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### 2. Error Response Format
```python
{
    "detail": "Error message here"
}
```

### 3. API Endpoint Naming
- All routes under `/api/` prefix
- Use plural nouns: `/api/{user_id}/tasks`
- Use resource IDs in path: `/api/{user_id}/tasks/{task_id}`
- Use query parameters for filtering: `?status=pending`

## Testing

### ⚠️ CRITICAL: Prerequisites Before Running Tests

**ALWAYS follow these steps before running any tests:**

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment (if not already created)
uv venv

# 3. Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# OR
.venv/Scripts/activate     # Windows

# 4. Install/sync all dependencies
uv sync

# 5. Now you can run tests
pytest tests/
```

**Why this is important:**
- Tests require all dependencies to be installed (pytest, FastAPI, SQLModel, etc.)
- Virtual environment isolation prevents dependency conflicts
- `uv sync` ensures all dependencies from `pyproject.toml` are installed
- Without this, tests will fail with import errors

### Unit Tests with Pytest
```python
# tests/test_tasks.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_tasks_unauthorized():
    """Test getting tasks without authentication"""
    response = client.get("/api/user123/tasks")
    assert response.status_code == 401

def test_create_task(auth_headers):
    """Test creating a new task"""
    response = client.post(
        "/api/user123/tasks",
        json={"title": "Test Task", "description": "Test description"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["completed"] == False
```

### Running Tests
```bash
# First, ensure virtual environment is activated and dependencies are synced!
# See "Prerequisites Before Running Tests" above

pytest tests/              # Run all tests
pytest tests/test_tasks.py # Run specific test file
pytest -v                  # Verbose output
pytest --cov=.             # With coverage report
```

## Running the Backend

### Development
```bash
cd backend
uv venv
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
uv sync
uvicorn main:app --reload --port 8000
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Database Migrations

For now, SQLModel auto-creates tables on startup. For production, consider:
- Alembic for migrations
- Database versioning
- Rollback strategies

## Best Practices

### 1. User Isolation (Security)
ALWAYS verify `user_id` matches authenticated user:
```python
if user_id != current_user_id:
    raise HTTPException(status_code=403, detail="Forbidden")
```

### 2. Input Validation
Use Pydantic models for all request data:
```python
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
```

### 3. Error Handling
Use HTTPException for all errors:
```python
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Task not found"
)
```

### 4. Database Session Management
Always use dependency injection for sessions:
```python
def get_tasks(session: Session = Depends(get_session)):
    # Session is automatically closed after request
    pass
```

### 5. Async Operations (When Needed)
For I/O-bound operations, use async:
```python
@router.get("/{user_id}/tasks")
async def get_tasks(
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(Task))
    return result.scalars().all()
```

## Deployment

### Hugging Face Spaces
1. Create new Space (FastAPI template)
2. Upload backend files
3. Add secrets in Space settings:
   - `DATABASE_URL`
   - `BETTER_AUTH_SECRET`
4. Deploy automatically

### Alternative: Railway, Render, or Fly.io
Follow similar process with platform-specific configuration.

## Common Tasks

### Add New API Endpoint
1. Define route in `routes/` file
2. Create request/response schemas in `schemas/`
3. Implement business logic
4. Add authentication and user isolation
5. Write tests

### Add New Database Model
1. Define model in `models.py`
2. Restart server (auto-creates table)
3. Consider migration strategy for production

### Add Middleware
1. Create middleware file in `middleware/`
2. Add to `main.py` with `app.add_middleware()`

---

**Remember**: Follow the monorepo conventions defined in the root CLAUDE.md. Reference API specs from `@specs/api/` and database schemas from `@specs/database/` when implementing features.

**Version**: 1.0.0 | **Last Updated**: 2025-12-08
