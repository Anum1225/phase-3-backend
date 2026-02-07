"""
Database connection and session management module.

This module provides:
- SQLModel engine configuration for Neon PostgreSQL
- Database session management with dependency injection
- Automatic table creation on startup
"""

import os
import time
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine

# Import models to register them with SQLModel metadata
# This ensures tables are created on startup
import models  # noqa: F401 - Phase 2 models (User, Task)
from src.models import Conversation, Message  # noqa: F401 - Phase 3 models

# Load environment variables from .env file
load_dotenv()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Validate DATABASE_URL exists
# For Hugging Face Spaces, DATABASE_URL should be set as a secret
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set. "
        "Please set it in Hugging Face Space secrets. "
        "Format: postgresql://user:password@host:port/database?sslmode=require"
    )

# Validate DATABASE_URL format (basic check)
if not DATABASE_URL.startswith("postgresql://"):
    raise ValueError(
        f"Invalid DATABASE_URL format. Expected postgresql:// URL, got: {DATABASE_URL[:20]}... "
        "Format: postgresql://user:password@host:port/database?sslmode=require"
    )

# Optional: Get database configuration from environment
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))

# Create SQLModel engine with connection pool configuration
engine = create_engine(
    DATABASE_URL,
    echo=DB_ECHO,  # Log SQL statements (development only)
    pool_size=DB_POOL_SIZE,  # Base connection pool size
    max_overflow=DB_MAX_OVERFLOW,  # Additional connections beyond pool_size
    pool_pre_ping=True,  # Verify connections before using them
)


def drop_all_tables():
    """
    Drop all database tables defined by SQLModel models.

    WARNING: This will delete all data in the database!
    Only use in development or when resetting the database schema.

    This function is useful when:
    - Schema has changed and tables need to be recreated
    - Starting fresh in development
    - Fixing schema mismatches (e.g., type incompatibilities)
    """
    SQLModel.metadata.drop_all(engine)


def create_db_and_tables():
    """
    Create all database tables defined by SQLModel models.

    This function should be called during application startup.
    It will create tables for all models that inherit from SQLModel
    and have table=True.

    If RESET_DB environment variable is set to "true", it will drop
    all existing tables before creating new ones (useful for development).

    Note: Creates PostgreSQL enum types before creating tables that use them.
    This is required because SQLModel doesn't automatically create enum types.

    Example:
        @app.on_event("startup")
        def on_startup():
            create_db_and_tables()
    """
    # Optionally drop all tables first (for development/reset)
    reset_db = os.getenv("RESET_DB", "false").lower() == "true"
    if reset_db:
        print("WARNING: Dropping all existing tables (RESET_DB=true)")
        drop_all_tables()

    # Create PostgreSQL enum types before creating tables
    # SQLModel doesn't automatically create enum types, so we need to do it manually
    with engine.begin() as conn:
        # Create message_role enum type if it doesn't exist
        # Using DO block to handle "already exists" case gracefully
        conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE message_role AS ENUM ('user', 'assistant');
                EXCEPTION WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )

    # Create all tables
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI route handlers.

    This function provides a database session with automatic cleanup.
    Use it with FastAPI's Depends() for dependency injection.

    The session is created before the request and automatically closed
    after the request completes, ensuring no resource leaks.

    Example:
        from typing import Annotated
        from fastapi import Depends
        from sqlmodel import Session

        SessionDep = Annotated[Session, Depends(get_session)]

        @app.get("/users")
        def get_users(session: SessionDep):
            users = session.exec(select(User)).all()
            return users

    Yields:
        Session: SQLModel database session

    Note:
        - Session is automatically committed on success
        - Session is automatically rolled back on exception
        - Session is automatically closed after request
    """
    with Session(engine) as session:
        yield session
