"""
Authentication API routes.

This module provides endpoints for user authentication:
- POST /api/auth/register: User registration with email and password
- POST /api/auth/login: User login
- POST /api/auth/logout: User logout (client-side token removal)
- GET /api/auth/profile: Get user profile (to be implemented in Phase 7)
- PUT /api/auth/profile: Update user profile (to be implemented in Phase 7)
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from db import get_session
from lib.jwt_utils import create_access_token
from lib.password import hash_password, verify_password
from models import User
from middleware.jwt import get_current_user_id
from schemas.auth import (
    AuthResponse,
    UserLoginRequest,
    UserProfileUpdateRequest,
    UserRegisterRequest,
    UserResponse,
)

# Create router with authentication tag
router = APIRouter(tags=["authentication"])

# Type alias for database session dependency
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, name, and password. Returns JWT token for immediate authentication.",
    responses={
        201: {
            "description": "User successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "newuser@example.com",
                            "name": "New User",
                            "created_at": "2025-12-11T10:30:00Z",
                            "updated_at": "2025-12-11T10:30:00Z",
                            "is_active": True
                        }
                    }
                }
            }
        },
        409: {
            "description": "Email already registered",
            "content": {
                "application/json": {
                    "example": {"detail": "Email already registered"}
                }
            }
        },
        422: {
            "description": "Validation error (invalid email, weak password, etc.)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "password"],
                                "msg": "Password must contain at least 1 number",
                                "type": "value_error"
                            }
                        ]
                    }
                }
            }
        }
    }
)
def register_user(
    user_data: UserRegisterRequest,
    session: SessionDep
) -> AuthResponse:
    """
    Register a new user account.

    This endpoint:
    1. Validates user input (email format, password strength)
    2. Checks email uniqueness in database
    3. Hashes password with bcrypt
    4. Creates user record in database
    5. Generates JWT access token
    6. Returns token and user data

    Args:
        user_data: User registration data (email, name, password)
        session: Database session (injected)

    Returns:
        AuthResponse: JWT token and user data

    Raises:
        HTTPException 409: Email already registered
        HTTPException 422: Validation error (handled by Pydantic)

    Example:
        Request:
        ```json
        {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "SecurePass123!"
        }
        ```

        Response (201):
        ```json
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "newuser@example.com",
                "name": "New User",
                "created_at": "2025-12-11T10:30:00Z",
                "updated_at": "2025-12-11T10:30:00Z",
                "is_active": True
            }
        }
        ```

    Security:
        - Password is hashed with bcrypt before storage
        - Plaintext password is never stored or logged
        - JWT token expires after 7 days
        - Email uniqueness is enforced at database level
    """
    # Check if email already exists
    statement = select(User).where(User.email == user_data.email)
    existing_user = session.exec(statement).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Hash password with bcrypt
    password_hash = hash_password(user_data.password)

    # Create new user
    new_user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=password_hash,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True
    )

    # Save to database
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    # Generate JWT access token
    access_token = create_access_token(
        user_id=new_user.id,
        email=new_user.email
    )

    # Convert User model to UserResponse (excludes password_hash)
    user_response = UserResponse.model_validate(new_user)

    # Return authentication response
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user with email and password. Returns JWT token on success.",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "user@example.com",
                            "name": "John Doe",
                            "created_at": "2025-12-11T10:30:00Z",
                            "updated_at": "2025-12-11T10:30:00Z",
                            "is_active": True
                        }
                    }
                }
            }
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid email or password"}
                }
            }
        }
    }
)
def login_user(
    login_data: UserLoginRequest,
    session: SessionDep
) -> AuthResponse:
    """
    Authenticate user and generate JWT token.

    This endpoint:
    1. Validates user input (email format)
    2. Fetches user from database by email
    3. Verifies password hash
    4. Generates JWT access token
    5. Returns token and user data

    Security Features:
    - Generic error messages to prevent user enumeration
    - Timing attack prevention (always hash password even if user doesn't exist)
    - Constant-time password verification

    Args:
        login_data: Login credentials (email, password)
        session: Database session (injected)

    Returns:
        AuthResponse: JWT token and user data

    Raises:
        HTTPException 401: Invalid email or password

    Example:
        Request:
        ```json
        {
            "email": "user@example.com",
            "password": "SecurePass123!"
        }
        ```

        Response (200):
        ```json
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "name": "John Doe",
                "created_at": "2025-12-11T10:30:00Z",
                "updated_at": "2025-12-11T10:30:00Z",
                "is_active": True
            }
        }
        ```

    Security Notes:
        - NEVER reveal whether email exists or password is wrong
        - Always use same error message: "Invalid email or password"
        - Perform password hash even if user doesn't exist (timing attack prevention)
        - Failed logins should not leak information
    """
    # Fetch user from database
    statement = select(User).where(User.email == login_data.email)
    user = session.exec(statement).first()

    # Timing attack prevention: always hash password even if user doesn't exist
    # This ensures response time is consistent for valid/invalid emails
    is_valid = False
    if user:
        is_valid = verify_password(login_data.password, user.password_hash)
    else:
        # Hash a dummy password to maintain constant time
        hash_password("dummy_password_for_timing_consistency")

    # Generic error message - don't reveal if email or password was wrong
    if not user or not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )

    # Generate JWT access token
    access_token = create_access_token(
        user_id=user.id,
        email=user.email
    )

    # Convert User model to UserResponse
    user_response = UserResponse.model_validate(user)

    # Return authentication response
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Logout user by instructing client to remove JWT token. Server-side tokens are stateless and expire after 7 days.",
    responses={
        200: {
            "description": "Logout successful",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Logout successful. Please remove token from client."
                    }
                }
            }
        }
    }
)
def logout_user():
    """
    Logout user (client-side token removal).

    Since JWT tokens are stateless, the server cannot invalidate them.
    The client is responsible for removing the token from storage.

    Client Implementation:
        1. Remove token from localStorage/sessionStorage
        2. Clear any client-side user state
        3. Redirect to login page

    Returns:
        dict: Success message with logout instructions

    Example:
        Request:
        ```http
        POST /api/auth/logout
        Authorization: Bearer <token>
        ```

        Response (200):
        ```json
        {
            "message": "Logout successful. Please remove token from client."
        }
        ```

    Security Notes:
        - Client MUST remove token from storage
        - Token remains valid until expiration (7 days)
        - For immediate invalidation, consider token blacklist (future enhancement)
        - Client should clear all user-related state on logout

    Frontend Example (JavaScript):
        ```javascript
        // Remove token from localStorage
        localStorage.removeItem('access_token');

        // Clear user state
        setUser(null);

        // Redirect to login
        router.push('/login');
        ```
    """
    return {
        "message": "Logout successful. Please remove token from client."
    }


@router.get(
    "/auth/profile",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user profile",
    description="Get authenticated user's profile data. Requires valid JWT token.",
    responses={
        200: {
            "description": "Profile retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "user@example.com",
                        "name": "John Doe",
                        "created_at": "2025-12-11T10:30:00Z",
                        "updated_at": "2025-12-11T10:30:00Z",
                        "is_active": True
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - invalid or missing token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid token"}
                }
            }
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found"}
                }
            }
        }
    }
)
def get_profile(
    session: SessionDep,
    user_id: str = Depends(get_current_user_id)
) -> UserResponse:
    """
    Get authenticated user's profile.

    This endpoint retrieves the profile data for the currently
    authenticated user based on their JWT token.

    Args:
        user_id: User ID from JWT token (injected by get_current_user_id)
        session: Database session (injected)

    Returns:
        UserResponse: User profile data (without password_hash)

    Raises:
        HTTPException 401: Invalid or missing token
        HTTPException 404: User not found in database

    Example:
        Request:
        ```http
        GET /api/auth/profile
        Authorization: Bearer <token>
        ```

        Response (200):
        ```json
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2025-12-11T10:30:00Z",
            "updated_at": "2025-12-11T10:30:00Z",
            "is_active": true
        }
        ```

    Security:
        - JWT token required in Authorization header
        - User can only access their own profile
        - Password hash is never returned
    """
    # Fetch user from database
    user = session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Convert to UserResponse (excludes password_hash)
    return UserResponse.model_validate(user)


@router.put(
    "/auth/profile",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user profile",
    description="Update authenticated user's profile data (currently only name). Requires valid JWT token.",
    responses={
        200: {
            "description": "Profile updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "user@example.com",
                        "name": "Updated Name",
                        "created_at": "2025-12-11T10:30:00Z",
                        "updated_at": "2025-12-11T15:45:00Z",
                        "is_active": True
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - invalid or missing token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid token"}
                }
            }
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found"}
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "name"],
                                "msg": "ensure this value has at least 1 characters",
                                "type": "value_error.any_str.min_length"
                            }
                        ]
                    }
                }
            }
        }
    }
)
def update_profile(
    profile_data: UserProfileUpdateRequest,
    session: SessionDep,
    user_id: str = Depends(get_current_user_id)
) -> UserResponse:
    """
    Update authenticated user's profile.

    This endpoint allows users to update their profile information.
    Currently supports updating name only. Email cannot be changed.

    Args:
        profile_data: Profile update data (name)
        user_id: User ID from JWT token (injected by get_current_user_id)
        session: Database session (injected)

    Returns:
        UserResponse: Updated user profile data

    Raises:
        HTTPException 401: Invalid or missing token
        HTTPException 404: User not found in database
        HTTPException 422: Validation error (handled by Pydantic)

    Example:
        Request:
        ```http
        PUT /api/auth/profile
        Authorization: Bearer <token>
        Content-Type: application/json

        {
            "name": "Jane Doe"
        }
        ```

        Response (200):
        ```json
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "name": "Jane Doe",
            "created_at": "2025-12-11T10:30:00Z",
            "updated_at": "2025-12-11T15:45:00Z",
            "is_active": true
        }
        ```

    Security:
        - JWT token required in Authorization header
        - User can only update their own profile
        - Email cannot be changed (not included in update schema)
        - updated_at timestamp is automatically set
    """
    # Fetch user from database
    user = session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update name if provided
    if profile_data.name is not None:
        user.name = profile_data.name

    # Update timestamp
    user.updated_at = datetime.utcnow()

    # Save changes
    session.add(user)
    session.commit()
    session.refresh(user)

    # Convert to UserResponse
    return UserResponse.model_validate(user)
