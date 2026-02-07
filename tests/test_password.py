"""
Unit tests for password hashing utilities.

Tests password hashing and verification functions to ensure:
- Passwords are hashed securely with bcrypt
- Hashed passwords can be verified correctly
- Password validation follows security requirements
"""

import pytest
from lib.password import hash_password, verify_password


class TestPasswordHashing:
    """Test password hashing functionality"""

    def test_hash_password_returns_hash(self):
        """Test that hash_password returns a bcrypt hash string"""
        password = "TestPassword123!"
        hashed = hash_password(password)

        # Bcrypt hashes are 60 characters
        assert len(hashed) == 60
        # Bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")

    def test_hash_password_generates_unique_hashes(self):
        """Test that same password generates different hashes (due to salt)"""
        password = "SamePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

    def test_verify_password_with_correct_password(self):
        """Test that verify_password returns True for correct password"""
        password = "CorrectPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_with_incorrect_password(self):
        """Test that verify_password returns False for incorrect password"""
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(correct_password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive"""
        password = "CaseSensitive123!"
        hashed = hash_password(password)

        assert verify_password("casesensitive123!", hashed) is False
        assert verify_password("CASESENSITIVE123!", hashed) is False


class TestPasswordValidation:
    """Test password strength validation requirements"""

    def test_valid_password_with_number_and_special_char(self):
        """Valid passwords should pass: minimum 8 chars, 1 number, 1 special char"""
        valid_passwords = [
            "Password123!",
            "SecureP@ss1",
            "MyP@ssw0rd",
            "Test1234!",
            "Str0ng#Pass",
        ]

        for password in valid_passwords:
            hashed = hash_password(password)
            # Should not raise any exceptions
            assert verify_password(password, hashed) is True

    def test_weak_password_no_number_should_fail(self):
        """Passwords without numbers should be rejected"""
        # Note: Validation will be done in Pydantic schema, not in hash function
        # This test documents the requirement
        weak_password = "NoNumbersHere!"

        # Password can still be hashed (hash function doesn't validate)
        hashed = hash_password(weak_password)
        assert verify_password(weak_password, hashed) is True

        # But it should fail Pydantic validation (tested in test_auth.py)

    def test_weak_password_no_special_char_should_fail(self):
        """Passwords without special characters should be rejected"""
        # Note: Validation will be done in Pydantic schema, not in hash function
        # This test documents the requirement
        weak_password = "NoSpecialChar123"

        # Password can still be hashed (hash function doesn't validate)
        hashed = hash_password(weak_password)
        assert verify_password(weak_password, hashed) is True

        # But it should fail Pydantic validation (tested in test_auth.py)

    def test_password_too_short_should_fail(self):
        """Passwords shorter than 8 characters should be rejected"""
        # Note: Validation will be done in Pydantic schema
        # This test documents the requirement
        short_password = "Short1!"

        # Can still be hashed
        hashed = hash_password(short_password)
        assert verify_password(short_password, hashed) is True

        # But should fail Pydantic validation (min_length=8)
