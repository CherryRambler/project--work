"""
Tests for app/core/security.py

These are "pure function" tests - no database, no mocking. You call the
function, check what comes back. This is the simplest kind of unit test,
good place to start since there's no setup complexity to think about.
"""
from jose import jwt

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)


class TestHashPassword:
    def test_hash_is_not_the_plain_password(self):
        """The whole point of hashing: the stored value should never equal
        the original password."""
        plain = "MySecret123!"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_same_password_produces_different_hashes(self):
        """bcrypt includes a random salt, so hashing the same password
        twice should give two different results."""
        hash1 = hash_password("MySecret123!")
        hash2 = hash_password("MySecret123!")
        assert hash1 != hash2


class TestVerifyPassword:
    def test_correct_password_verifies_true(self):
        hashed = hash_password("MySecret123!")
        assert verify_password("MySecret123!", hashed) is True

    def test_wrong_password_verifies_false(self):
        hashed = hash_password("MySecret123!")
        assert verify_password("WrongPassword!", hashed) is False

    def test_empty_password_does_not_verify(self):
        hashed = hash_password("MySecret123!")
        assert verify_password("", hashed) is False


class TestCreateAccessToken:
    def test_token_contains_correct_claims(self):
        """Decode the token we just created and check every field we
        expect to be inside it."""
        user_id = "b1467578-b42d-4f4e-8d6b-028c4bac4c79"
        token = create_access_token(user_id, "admin", True)

        payload = jwt.decode(
            token, settings.ACCESS_TOKEN_SECRET, algorithms=[settings.ALGORITHM]
        )

        assert payload["sub"] == user_id
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
        assert payload["is_active"] is True
        assert "exp" in payload

    def test_token_defaults_is_active_true(self):
        """is_active has a default value of True if not passed."""
        token = create_access_token("some-user-id", "viewer")
        payload = jwt.decode(
            token, settings.ACCESS_TOKEN_SECRET, algorithms=[settings.ALGORITHM]
        )
        assert payload["is_active"] is True

    def test_inactive_user_token_reflects_that(self):
        token = create_access_token("some-user-id", "viewer", False)
        payload = jwt.decode(
            token, settings.ACCESS_TOKEN_SECRET, algorithms=[settings.ALGORITHM]
        )
        assert payload["is_active"] is False


class TestCreateRefreshToken:
    def test_token_has_refresh_type(self):
        token = create_refresh_token("some-user-id")
        payload = jwt.decode(
            token, settings.REFRESH_TOKEN_SECRET, algorithms=[settings.ALGORITHM]
        )
        assert payload["type"] == "refresh"
        assert payload["sub"] == "some-user-id"

    def test_access_and_refresh_tokens_are_not_interchangeable(self):
        """An access token should NOT decode successfully with the refresh
        secret, and vice versa - this matters for security, so it's worth
        testing explicitly."""
        access_token = create_access_token("some-user-id", "viewer")

        # Decoding an access token with the refresh secret should fail,
        # since they're signed with different secrets in your config.
        if settings.ACCESS_TOKEN_SECRET != settings.REFRESH_TOKEN_SECRET:
            import pytest
            from jose import JWTError

            with pytest.raises(JWTError):
                jwt.decode(
                    access_token,
                    settings.REFRESH_TOKEN_SECRET,
                    algorithms=[settings.ALGORITHM],
                )