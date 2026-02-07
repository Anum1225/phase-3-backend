"""
JWT verification middleware for protected routes.

This module provides FastAPI dependency functions for JWT token verification.
Use these dependencies to protect routes that require authentication.

Security Features:
- Bearer token extraction from Authorization header
- JWT signature validation with shared secret
- Token expiration checking
- User ID extraction from token payload

Example:
    from fastapi import Depends
    from middleware.jwt import get_current_user_id

    @app.get("/api/protected")
    def protected_route(user_id: str = Depends(get_current_user_id)):
        return {"message": f"Hello user {user_id}"}
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lib.jwt_utils import verify_token

# HTTPBearer security scheme for OpenAPI docs
# This automatically adds "Authorize" button in Swagger UI
security = HTTPBearer()


def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Verify JWT token from Authorization header.

    This dependency extracts and verifies the JWT token from the
    Authorization header. It validates the signature and expiration.

    Args:
        credentials: HTTPBearer credentials from Authorization header

    Returns:
        dict: Decoded token payload containing:
            - sub: User ID
            - email: User email
            - iat: Issued at timestamp
            - exp: Expiration timestamp

    Raises:
        HTTPException 401: Token expired or invalid

    Example:
        Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

        Decoded payload:
        {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "iat": 1680000000,
            "exp": 1680604800
        }

    Security Notes:
        - Token must be prefixed with "Bearer " in header
        - Invalid tokens return 401 Unauthorized
        - Expired tokens return 401 with "Token has expired" message
        - Tampered tokens return 401 with "Invalid token" message
    """
    token = credentials.credentials

    try:
        # Verify token using lib/jwt_utils.py
        # This checks signature and expiration automatically
        payload = verify_token(token)
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(token_payload: dict = Depends(verify_jwt_token)) -> str:
    """
    Extract user ID from verified JWT token.

    This dependency builds on verify_jwt_token to extract the user ID
    from the token payload. Use this in protected routes to get the
    authenticated user's ID.

    Args:
        token_payload: Verified token payload (injected by verify_jwt_token)

    Returns:
        str: User ID (UUID string)

    Raises:
        HTTPException 401: User ID not found in token

    Example:
        @app.get("/api/tasks")
        def get_tasks(user_id: str = Depends(get_current_user_id)):
            # user_id is "550e8400-e29b-41d4-a716-446655440000"
            tasks = db.query(Task).filter(Task.user_id == user_id).all()
            return tasks

    Usage Patterns:
        # Pattern 1: Direct dependency
        @app.get("/api/me")
        def get_me(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}

        # Pattern 2: Type alias for cleaner code
        from typing import Annotated
        UserIdDep = Annotated[str, Depends(get_current_user_id)]

        @app.get("/api/profile")
        def get_profile(user_id: UserIdDep):
            return {"user_id": user_id}

    Security Notes:
        - Always verify user_id matches resource owner
        - Implement user isolation: users can only access their own data
        - Fail closed: missing user_id raises 401, not 200 with error
    """
    # Extract user ID from 'sub' claim (standard JWT claim for subject)
    user_id = token_payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id
