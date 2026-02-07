"""
Integration tests for authentication endpoints.

Tests the full authentication flow including:
- User registration
- User login
- Session persistence
- Logout
- Protected routes
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from main import app
from db import get_session
from models import User


# Test database setup
@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh test database for each test"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create test client with test database"""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ===== User Story 1: Registration Tests =====


class TestUserRegistration:
    """Test user registration endpoint (T015-T018)"""

    def test_register_success_returns_201_and_token(self, client: TestClient):
        """T015: Test successful registration returns 201 and JWT token"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "name": "New User",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert "user" in data

        # Verify token type
        assert data["token_type"] == "bearer"

        # Verify user data
        user = data["user"]
        assert user["email"] == "newuser@example.com"
        assert user["name"] == "New User"
        assert "password_hash" not in user  # Password should not be returned
        assert "id" in user
        assert "created_at" in user

    def test_register_duplicate_email_returns_409(self, client: TestClient):
        """T016: Test registering same email twice returns 409 Conflict"""
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "name": "First User",
                "password": "Password123!",
            },
        )

        # Try to register with same email
        response = client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "name": "Second User",
                "password": "DifferentPass123!",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert "already registered" in data["detail"].lower()

    def test_register_invalid_email_returns_400(self, client: TestClient):
        """T017: Test invalid email format returns 400 validation error"""
        invalid_emails = [
            "notanemail",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com",
            "double@@domain.com",
        ]

        for invalid_email in invalid_emails:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": invalid_email,
                    "name": "Test User",
                    "password": "ValidPass123!",
                },
            )

            assert response.status_code == 422  # FastAPI validation error
            data = response.json()
            assert "detail" in data

    def test_register_weak_password_returns_400(self, client: TestClient):
        """T018: Test weak passwords return 400 validation error"""
        weak_passwords = [
            "short",  # Too short (< 8 chars)
            "NoNumbers!",  # No numbers
            "NoSpecial123",  # No special characters
            "        ",  # Whitespace only
        ]

        for weak_password in weak_passwords:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": f"test{weak_password}@example.com",
                    "name": "Test User",
                    "password": weak_password,
                },
            )

            # Should fail validation (422) or return bad request (400)
            assert response.status_code in [400, 422]
            data = response.json()
            assert "detail" in data


# ===== User Story 2: Login Tests (will be implemented later) =====


class TestUserLogin:
    """Test user login endpoint (T026-T029)"""

    @pytest.mark.skip(reason="Will be implemented in Phase 4")
    def test_login_success_returns_200_and_token(self, client: TestClient):
        """T026: Test successful login returns 200 and JWT token"""
        pass

    @pytest.mark.skip(reason="Will be implemented in Phase 4")
    def test_login_incorrect_password_returns_401(self, client: TestClient):
        """T027: Test login with wrong password returns 401"""
        pass

    @pytest.mark.skip(reason="Will be implemented in Phase 4")
    def test_login_nonexistent_email_returns_401(self, client: TestClient):
        """T028: Test login with unregistered email returns 401"""
        pass

    @pytest.mark.skip(reason="Will be implemented in Phase 4")
    def test_login_timing_attack_prevention(self, client: TestClient):
        """T029: Test response times are consistent to prevent timing attacks"""
        pass


# ===== User Story 4: Secure API Tests (will be implemented later) =====


class TestSecureAPI:
    """Test JWT token validation (T037-T040)"""

    @pytest.mark.skip(reason="Will be implemented in Phase 5")
    def test_protected_route_with_valid_token_succeeds(self, client: TestClient):
        """T037: Test protected route with valid Bearer token succeeds"""
        pass

    @pytest.mark.skip(reason="Will be implemented in Phase 5")
    def test_protected_route_without_token_returns_401(self, client: TestClient):
        """T038: Test protected route without token returns 401"""
        pass

    @pytest.mark.skip(reason="Will be implemented in Phase 5")
    def test_protected_route_with_expired_token_returns_401(self, client: TestClient):
        """T039: Test protected route with expired token returns 401"""
        pass

    @pytest.mark.skip(reason="Will be implemented in Phase 5")
    def test_protected_route_with_tampered_token_returns_401(self, client: TestClient):
        """T040: Test protected route with invalid signature returns 401"""
        pass


# ===== User Story 3: Session Persistence Tests (will be implemented later) =====


class TestSessionPersistence:
    """Test logout and session management (T046-T048)"""

    @pytest.mark.skip(reason="Will be implemented in Phase 6")
    def test_logout_returns_200(self, client: TestClient):
        """T046: Test logout with valid token returns 200"""
        pass

    @pytest.mark.skip(reason="Will be implemented in Phase 6")
    def test_session_persistence_multiple_requests(self, client: TestClient):
        """T047: Test multiple requests with same token succeed"""
        pass

    @pytest.mark.skip(reason="Will be implemented in Phase 6")
    def test_expired_session_returns_401(self, client: TestClient):
        """T048: Test expired token returns 401"""
        pass
