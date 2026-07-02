"""
Tests for the register() and login() functions in app/routers/auth.py

These are your most realistic tests: the actual endpoint functions,
called directly (skipping the HTTP layer, which is normal for unit
testing - FastAPI endpoint functions are just plain async functions).

The database is mocked (see conftest.py's `mock_db` fixture), so no
real Postgres connection is needed. We control exactly what the fake
`db.execute(...)` calls return, to force each function down a specific
code path (duplicate email, wrong password, success, etc.) and check
it behaves correctly.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.security import hash_password
from app.models.user import User, RoleEnum, AccountStatusEnum
from app.routers.auth import register, login
from app.schemas.auth import RegisterSchema, LoginSchema
from tests.conftest import make_scalar_result


def fake_request():
    """A minimal stand-in for FastAPI's Request object, just enough for
    get_ip() to work without crashing."""
    request = MagicMock()
    request.headers.get.return_value = None
    request.client.host = "127.0.0.1"
    return request


class TestRegister:
    async def test_duplicate_email_is_rejected(self, mock_db):
        existing_user = User(
            user_id=uuid.uuid4(), email="taken@example.com", user_name="x", phone_no="1"
        )
        # First db.execute call (email lookup) finds a user already
        mock_db.execute.return_value = make_scalar_result(existing_user)

        data = RegisterSchema(
            user_name="newuser",
            email="taken@example.com",
            phone_no="9999999999",
            password="Strong1!",
            role="viewer",
        )

        with pytest.raises(HTTPException) as exc_info:
            await register(data, fake_request(), mock_db)

        assert exc_info.value.status_code == 400
        assert "already registered" in exc_info.value.detail

    async def test_duplicate_username_is_rejected(self, mock_db):
        # 1st execute (email check) -> no match, 2nd (username check) -> match
        mock_db.execute.side_effect = [
            make_scalar_result(None),
            make_scalar_result(User(user_id=uuid.uuid4(), user_name="taken")),
        ]

        data = RegisterSchema(
            user_name="taken",
            email="new@example.com",
            phone_no="9999999999",
            password="Strong1!",
            role="viewer",
        )

        with pytest.raises(HTTPException) as exc_info:
            await register(data, fake_request(), mock_db)

        assert exc_info.value.status_code == 400
        assert "Username" in exc_info.value.detail

    async def test_invalid_role_is_rejected(self, mock_db):
        # email, username, phone checks all pass (no duplicates found)
        mock_db.execute.side_effect = [
            make_scalar_result(None),
            make_scalar_result(None),
            make_scalar_result(None),
        ]

        # Pydantic's RegisterSchema.role is just `Optional[str]`, so an
        # invalid value like "superadmin" passes schema validation and
        # only gets caught by the router's RoleEnum(...) conversion.
        data = RegisterSchema(
            user_name="newuser",
            email="new@example.com",
            phone_no="9999999999",
            password="Strong1!",
            role="superadmin",
        )

        with pytest.raises(HTTPException) as exc_info:
            await register(data, fake_request(), mock_db)

        assert exc_info.value.status_code == 400
        assert "Invalid role" in exc_info.value.detail

    async def test_successful_registration_commits_and_returns_message(self, mock_db):
        mock_db.execute.side_effect = [
            make_scalar_result(None),  # email check
            make_scalar_result(None),  # username check
            make_scalar_result(None),  # phone check
        ]

        data = RegisterSchema(
            user_name="newuser",
            email="new@example.com",
            phone_no="9999999999",
            password="Strong1!",
            role="viewer",
        )

        result = await register(data, fake_request(), mock_db)

        assert result == {"message": "User created"}
        mock_db.add.assert_called()  # user object added
        mock_db.commit.assert_awaited_once()


class TestLogin:
    def _make_active_user(self, password="Strong1!"):
        return User(
            user_id=uuid.uuid4(),
            email="test@example.com",
            user_name="testuser",
            phone_no="1234567890",
            hashed_password=hash_password(password),
            role=RoleEnum.viewer,
            account_status=AccountStatusEnum.ACTIVATED,
            failed_login_attempts=0,
            locked_until=None,
        )

    async def test_unknown_email_is_rejected(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)

        data = LoginSchema(email="nobody@example.com", password="whatever1!A", platform="web")

        with pytest.raises(HTTPException) as exc_info:
            await login(data, fake_request(), mock_db)

        assert exc_info.value.status_code == 401

    async def test_disabled_account_is_rejected(self, mock_db):
        user = self._make_active_user()
        user.account_status = AccountStatusEnum.DEACTIVATED
        mock_db.execute.return_value = make_scalar_result(user)

        data = LoginSchema(email=user.email, password="Strong1!", platform="web")

        with pytest.raises(HTTPException) as exc_info:
            await login(data, fake_request(), mock_db)

        assert exc_info.value.status_code == 403
        assert "disabled" in exc_info.value.detail

    async def test_wrong_password_is_rejected(self, mock_db):
        user = self._make_active_user(password="CorrectPass1!")
        mock_db.execute.return_value = make_scalar_result(user)

        data = LoginSchema(email=user.email, password="WrongPass1!", platform="web")

        with pytest.raises(HTTPException) as exc_info:
            await login(data, fake_request(), mock_db)

        assert exc_info.value.status_code == 401
        assert user.failed_login_attempts == 1  # incremented on failure

    async def test_successful_login_returns_tokens(self, mock_db):
        user = self._make_active_user(password="CorrectPass1!")
        mock_db.execute.return_value = make_scalar_result(user)

        data = LoginSchema(email=user.email, password="CorrectPass1!", platform="web")

        result = await login(data, fake_request(), mock_db)

        assert "access_token" in result
        assert "refresh_token" in result
        assert user.failed_login_attempts == 0
        mock_db.commit.assert_awaited_once()