"""
JWT token generation and validation utilities.

This module provides functions for creating and verifying JWT tokens
used for user authentication. Tokens are signed with a shared secret
and have a 7-day expiration period.

Security Features:
- HS256 algorithm (HMAC with SHA-256)
- 256-bit shared secret
- 7-day token expiration
- Automatic expiration validation
- Tamper-proof signatures

Example:
    from lib.jwt_utils import create_access_token, verify_token

    # Generate token during login/registration
    token = create_access_token(user_id="123", email="user@example.com")

    # Verify token on protected routes
    try:
        payload = verify_token(token)
        user_id = payload["sub"]  # "123"
    except jwt.ExpiredSignatureError:
        # Handle expired token
    except jwt.InvalidTokenError:
        # Handle invalid token
"""

import os
from datetime import datetime, timedelta
from typing import Dict

import jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("BETTER_AUTH_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Token expiration: 7 days (604800 seconds)
TOKEN_EXPIRATION_DAYS = 7

# Validate SECRET_KEY exists
if not SECRET_KEY:
    raise ValueError(
        "BETTER_AUTH_SECRET environment variable is not set. "
        "Generate with: openssl rand -hex 32"
    )


def create_access_token(user_id: str, email: str) -> str:
    """
    Generate a JWT access token for authenticated user.

    The token includes user identification and expiration timestamp.
    It is signed with the shared secret and can be verified by both
    frontend and backend.

    Token Payload:
        - sub (subject): User ID
        - email: User's email address
        - iat (issued at): Token creation timestamp (UTC)
        - exp (expiration): Token expiration timestamp (UTC)

    Args:
        user_id (str): Unique user identifier (UUID)
        email (str): User's email address

    Returns:
        str: Signed JWT token string

    Example:
        >>> token = create_access_token("abc-123", "user@example.com")
        >>> len(token) > 100  # JWT tokens are long strings
        True
        >>> token.count('.') == 2  # JWT has 3 parts: header.payload.signature
        True

    Token Format:
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMiLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJpYXQiOjE2ODAwMDAwMDAsImV4cCI6MTY4MDYwNDgwMH0.signature

    Note:
        - Token is valid for 7 days from issuance
        - Frontend should store in localStorage or httpOnly cookie
        - Include in requests: Authorization: Bearer <token>
    """
    # Calculate expiration timestamp (7 days from now)
    exp_datetime = datetime.utcnow() + timedelta(days=TOKEN_EXPIRATION_DAYS)

    # Build JWT payload
    payload: Dict[str, any] = {
        "sub": user_id,  # Subject: user ID
        "email": email,  # User email
        "iat": datetime.utcnow(),  # Issued at
        "exp": exp_datetime,  # Expiration
    }

    # Encode and sign token
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return token


def verify_token(token: str) -> Dict[str, any]:
    """
    Verify and decode a JWT token.

    This function validates the token signature and expiration.
    If valid, it returns the decoded payload. If invalid or expired,
    it raises an appropriate exception.

    Args:
        token (str): JWT token string to verify

    Returns:
        Dict[str, any]: Decoded token payload containing:
            - sub: User ID
            - email: User email
            - iat: Issued at timestamp
            - exp: Expiration timestamp

    Raises:
        jwt.ExpiredSignatureError: Token has expired (past exp timestamp)
        jwt.InvalidTokenError: Token signature is invalid or malformed

    Example:
        >>> token = create_access_token("123", "user@example.com")
        >>> payload = verify_token(token)
        >>> payload["sub"]
        '123'
        >>> payload["email"]
        'user@example.com'

    Security Notes:
        - Always catch exceptions and return 401 Unauthorized
        - Use generic error messages to prevent information leakage
        - Expired tokens should require user to login again
        - Invalid tokens indicate tampering or wrong secret

    Usage in Middleware:
        try:
            payload = verify_token(token)
            user_id = payload["sub"]
            # Proceed with authenticated request
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
    """
    # Decode and verify token
    # jwt.decode automatically checks:
    # - Signature validity (using SECRET_KEY)
    # - Expiration (exp claim)
    # - Token structure
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    return payload
