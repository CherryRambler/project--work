"""
Tests for app/core/audit_logger.py

This is your first "mocked database" test. `write_audit_log` doesn't
return anything useful to check directly - what it DOES is call
`db.add(some_audit_log_object)`. So instead of checking a return value,
we check that db.add() was called with the correct data.

This is a common testing pattern: when a function's job is to "do
something" rather than "calculate something", you verify the *call*,
not a return value.
"""
import uuid

from app.core.audit_logger import write_audit_log
from app.models.audit_log import AuditLog


class TestWriteAuditLog:
    async def test_calls_db_add_with_audit_log(self, mock_db):
        user_id = uuid.uuid4()

        await write_audit_log(
            db=mock_db,
            action="LOGIN_SUCCESS",
            user_id=user_id,
            user_email="test@example.com",
            resource=f"user:{user_id}",
            detail="Login from web",
            ip_address="127.0.0.1",
        )

        # db.add should have been called exactly once
        mock_db.add.assert_called_once()

        # Grab the object it was called with, and check its fields
        logged_object = mock_db.add.call_args[0][0]
        assert isinstance(logged_object, AuditLog)
        assert logged_object.action == "LOGIN_SUCCESS"
        assert logged_object.user_id == user_id
        assert logged_object.user_email == "test@example.com"
        assert logged_object.success is True  # default value

    async def test_success_defaults_to_true(self, mock_db):
        await write_audit_log(db=mock_db, action="SOME_ACTION")
        logged_object = mock_db.add.call_args[0][0]
        assert logged_object.success is True

    async def test_can_log_a_failed_action(self, mock_db):
        await write_audit_log(db=mock_db, action="LOGIN_FAILED", success=False)
        logged_object = mock_db.add.call_args[0][0]
        assert logged_object.success is False

    async def test_optional_fields_default_to_none(self, mock_db):
        """user_id, user_email, resource, detail, ip_address should all
        be allowed to be omitted."""
        await write_audit_log(db=mock_db, action="SOME_ACTION")
        logged_object = mock_db.add.call_args[0][0]
        assert logged_object.user_id is None
        assert logged_object.user_email is None
        assert logged_object.resource is None
        assert logged_object.detail is None
        assert logged_object.ip_address is None