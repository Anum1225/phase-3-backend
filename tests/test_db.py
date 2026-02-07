"""
Database connection tests.

Tests use in-memory SQLite for fast, isolated testing.
No Neon connection required.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool


def test_database_engine_creation(engine):
    """Test that engine is created successfully"""
    assert engine is not None


def test_create_tables(engine):
    """Test that SQLModel can create tables"""
    # This should not raise any exceptions
    SQLModel.metadata.create_all(engine)


def test_session_creation(session: Session):
    """Test that database session is created successfully"""
    assert session is not None
    assert isinstance(session, Session)


def test_session_query(session: Session):
    """Test that session can execute queries"""
    # Execute a simple query
    result = session.exec("SELECT 1 as test_column")
    row = result.first()
    assert row is not None
    assert row[0] == 1


def test_session_context_manager():
    """Test that session context manager works properly"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with Session(engine) as session:
        result = session.exec("SELECT 1")
        assert result.first()[0] == 1

    # Session should be closed after exiting context manager
    # (No way to directly test this, but the context manager handles it)


def test_user_model_creation(session: Session):
    """Test creating a User model instance"""
    from models import User

    user = User(email="test@example.com", name="Test User")
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.created_at is not None


def test_user_model_query(session: Session):
    """Test querying User model"""
    from models import User

    # Create test user
    user = User(email="query@example.com", name="Query User")
    session.add(user)
    session.commit()

    # Query by email
    statement = select(User).where(User.email == "query@example.com")
    found_user = session.exec(statement).first()

    assert found_user is not None
    assert found_user.email == "query@example.com"
    assert found_user.name == "Query User"


def test_user_model_unique_constraint(session: Session):
    """Test that email unique constraint is enforced"""
    from sqlalchemy.exc import IntegrityError

    from models import User

    # Create first user
    user1 = User(email="unique@example.com", name="User One")
    session.add(user1)
    session.commit()

    # Try to create second user with same email
    user2 = User(email="unique@example.com", name="User Two")
    session.add(user2)

    # Should raise IntegrityError due to unique constraint
    with pytest.raises(IntegrityError):
        session.commit()
