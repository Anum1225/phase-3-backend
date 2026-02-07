"""
Pytest configuration and fixtures for backend tests.

This module provides:
- Test database session fixtures using in-memory SQLite
- FastAPI TestClient fixture with dependency overrides
- Common test utilities
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool


@pytest.fixture(name="engine")
def engine_fixture():
    """
    Create in-memory SQLite engine for testing.

    Uses StaticPool to ensure the same database is used across
    all connections in a single test.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """
    Create a fresh database session for each test.

    The session is automatically rolled back after the test,
    ensuring test isolation.
    """
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Create FastAPI TestClient with overridden database session.

    Overrides the get_session dependency to use the test database session.
    This ensures all API endpoints use the in-memory test database.

    Usage:
        def test_endpoint(client: TestClient):
            response = client.get("/")
            assert response.status_code == 200
    """
    # Import here to avoid circular dependencies
    from main import app
    from db import get_session

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
