"""
Password hashing utilities using bcrypt via passlib.

This module provides secure password hashing and verification functions
for user authentication. Passwords are hashed using bcrypt with 12 rounds
(passlib default), providing strong protection against brute-force attacks.

Security Features:
- Bcrypt algorithm (slow by design, resistant to brute-force)
- Automatic salt generation
- Constant-time password verification
- OWASP recommended approach

Example:
    from lib.password import hash_password, verify_password

    # Hash password during registration
    hashed = hash_password("SecurePass123!")

    # Verify password during login
    is_valid = verify_password("SecurePass123!", hashed)  # True
    is_valid = verify_password("WrongPassword", hashed)   # False
"""

import bcrypt


def _truncate_to_72_bytes(password: str) -> bytes:
    """
    Truncate password to bcrypt's 72-byte limit safely.
    Returns bytes (bcrypt requires bytes).
    """
    password_bytes = password.encode("utf-8")

    if len(password_bytes) <= 72:
        return password_bytes

    truncated = password_bytes[:72]

    # Ensure valid UTF-8
    while True:
        try:
            truncated.decode("utf-8")
            break
        except UnicodeDecodeError:
            truncated = truncated[:-1]

    return truncated


def hash_password(password: str) -> str:
    password_bytes = _truncate_to_72_bytes(password)

    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = _truncate_to_72_bytes(plain_password)

    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
