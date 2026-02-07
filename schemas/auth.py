"""
Authentication request/response Pydantic schemas.

This module defines schemas for authentication endpoints using Pydantic.
Schemas provide automatic validation, serialization, and API documentation.

Schemas:
    - ErrorResponse: Standard error response format
    - UserRegisterRequest: User registration request with validation
    - UserResponse: User data response (excludes password_hash)
    - AuthResponse: Authentication response with JWT token and user data
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ErrorResponse(BaseModel):
    """
    Standard error response format for all API endpoints.

    Used for validation errors, authentication failures, and general errors.
    Provides consistent error format across the API.

    Attributes:
        detail: Human-readable error message

    Example:
        >>> error = ErrorResponse(detail="Invalid email or password")
        >>> error.model_dump()
        {'detail': 'Invalid email or password'}

    Usage in FastAPI:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

        # FastAPI automatically wraps this in ErrorResponse format
    """

    detail: str

    class Config:
        """Pydantic configuration with examples for API docs"""

        json_schema_extra = {"example": {"detail": "Invalid email or password"}}


class UserRegisterRequest(BaseModel):
    """
    User registration request schema.

    Validates user registration data with strong password requirements:
    - Minimum 8 characters
    - At least 1 number
    - At least 1 special character (!@#$%^&*(),.?":{}|<>)

    Attributes:
        email: Valid email address (unique in database)
        name: User's display name (1-100 characters)
        password: Strong password meeting security requirements

    Example:
        >>> request = UserRegisterRequest(
        ...     email="user@example.com",
        ...     name="John Doe",
        ...     password="SecurePass123!"
        ... )
    """

    email: EmailStr = Field(
        ...,
        description="User's email address (must be unique)",
        json_schema_extra={"example": "user@example.com"},
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's display name",
        json_schema_extra={"example": "John Doe"},
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=72,  # Bcrypt's maximum byte limit
        description="Strong password (8-72 chars, 1 number, 1 special char)",
        json_schema_extra={"example": "SecurePass123!"},
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength requirements.

        Password must contain:
        - At least 1 number
        - At least 1 special character

        Args:
            v: Password string

        Returns:
            str: Validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        # Check for at least one number
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least 1 number")

        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least 1 special character")

        return v

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "name": "New User",
                "password": "SecurePass123!",
            }
        }


class UserLoginRequest(BaseModel):
    """
    User login request schema.

    Simple email and password authentication.
    Password strength is not validated here (only during registration).

    Attributes:
        email: User's registered email address
        password: User's password (validated against stored hash)

    Example:
        >>> request = UserLoginRequest(
        ...     email="user@example.com",
        ...     password="SecurePass123!"
        ... )
    """

    email: EmailStr = Field(
        ...,
        description="User's email address",
        json_schema_extra={"example": "user@example.com"},
    )

    password: str = Field(
        ...,
        description="User's password",
        json_schema_extra={"example": "SecurePass123!"},
    )

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {"email": "user@example.com", "password": "SecurePass123!"}
        }


class UserResponse(BaseModel):
    """
    User data response schema.

    Returns user information without sensitive fields (password_hash).
    Used in registration, login, and profile responses.

    Attributes:
        id: User's unique identifier (UUID)
        email: User's email address
        name: User's display name
        created_at: Account creation timestamp
        updated_at: Last profile update timestamp
        is_active: Account active status

    Example:
        >>> user = UserResponse(
        ...     id="abc-123",
        ...     email="user@example.com",
        ...     name="John Doe",
        ...     created_at=datetime.utcnow(),
        ...     updated_at=datetime.utcnow(),
        ...     is_active=True
        ... )
    """

    id: str = Field(..., description="User's unique identifier (UUID)")
    email: str = Field(..., description="User's email address")
    name: str = Field(..., description="User's display name")
    created_at: datetime = Field(..., description="Account creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
    is_active: bool = Field(default=True, description="Account active status")

    class Config:
        """Pydantic configuration"""

        from_attributes = True  # Enable ORM mode for SQLModel compatibility
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "name": "John Doe",
                "created_at": "2025-12-11T10:30:00Z",
                "updated_at": "2025-12-11T10:30:00Z",
                "is_active": True,
            }
        }


class AuthResponse(BaseModel):
    """
    Authentication response schema.

    Returns JWT access token and user data after successful
    registration or login.

    Attributes:
        access_token: JWT token for authenticated requests
        token_type: Token type (always "bearer")
        user: User data (UserResponse)

    Example:
        >>> response = AuthResponse(
        ...     access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ...     token_type="bearer",
        ...     user=user_data
        ... )

    Usage:
        Client should store access_token and include in requests:
        Authorization: Bearer <access_token>
    """

    access_token: str = Field(
        ...,
        description="JWT access token (valid for 7 days)",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )

    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
        json_schema_extra={"example": "bearer"},
    )

    user: UserResponse = Field(..., description="User data (without password_hash)")

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "name": "John Doe",
                    "created_at": "2025-12-11T10:30:00Z",
                    "updated_at": "2025-12-11T10:30:00Z",
                    "is_active": True,
                },
            }
        }


class UserProfileUpdateRequest(BaseModel):
    """
    User profile update request schema.

    Allows updating user's display name.
    Email cannot be changed after registration.

    Attributes:
        name: New display name (optional)

    Example:
        >>> request = UserProfileUpdateRequest(name="Jane Doe")
    """

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="New display name",
        json_schema_extra={"example": "Jane Doe"},
    )

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {"example": {"name": "Updated Name"}}
