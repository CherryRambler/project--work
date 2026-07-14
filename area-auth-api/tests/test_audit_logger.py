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
        print(f"\n[DEBUG] calling write_audit_log with:")
        print(f"[DEBUG]   action       = 'LOGIN_SUCCESS'")
        print(f"[DEBUG]   user_id      = {user_id}")
        print(f"[DEBUG]   user_email   = 'test@example.com'")
        print(f"[DEBUG]   resource     = 'user:{user_id}'")
        print(f"[DEBUG]   detail       = 'Login from web'")
        print(f"[DEBUG]   ip_address   = '127.0.0.1'")

        await write_audit_log(
            db=mock_db,
            action="LOGIN_SUCCESS",
            user_id=user_id,
            user_email="test@example.com",
            resource=f"user:{user_id}",
            detail="Login from web",
            ip_address="127.0.0.1",
        )

        print(f"[DEBUG] mock_db.add call count : {mock_db.add.call_count}")
        # db.add should have been called exactly once
        mock_db.add.assert_called_once()

        # Grab the object it was called with, and check its fields
        logged_object = mock_db.add.call_args[0][0]
        print(f"[DEBUG] object passed to db.add : {logged_object!r}")
        print(f"[DEBUG]   type         : {type(logged_object).__name__}")
        print(f"[DEBUG]   action       : {logged_object.action!r}")
        print(f"[DEBUG]   user_id      : {logged_object.user_id}")
        print(f"[DEBUG]   user_email   : {logged_object.user_email!r}")
        print(f"[DEBUG]   success      : {logged_object.success}")
        assert isinstance(logged_object, AuditLog)
        assert logged_object.action == "LOGIN_SUCCESS"
        assert logged_object.user_id == user_id
        assert logged_object.user_email == "test@example.com"
        assert logged_object.success is True  # default value

    async def test_success_defaults_to_true(self, mock_db):
        print(f"\n[DEBUG] calling write_audit_log with action='SOME_ACTION' and no success argument")
        await write_audit_log(db=mock_db, action="SOME_ACTION")
        logged_object = mock_db.add.call_args[0][0]
        print(f"[DEBUG] logged_object.success : {logged_object.success}")
        assert logged_object.success is True

    async def test_can_log_a_failed_action(self, mock_db):
        print(f"\n[DEBUG] calling write_audit_log with action='LOGIN_FAILED', success=False")
        await write_audit_log(db=mock_db, action="LOGIN_FAILED", success=False)
        logged_object = mock_db.add.call_args[0][0]
        print(f"[DEBUG] logged_object.action  : {logged_object.action!r}")
        print(f"[DEBUG] logged_object.success : {logged_object.success}")
        assert logged_object.success is False

    async def test_optional_fields_default_to_none(self, mock_db):
        """user_id, user_email, resource, detail, ip_address should all
        be allowed to be omitted."""
        print(f"\n[DEBUG] calling write_audit_log with only action='SOME_ACTION' (all optional fields omitted)")
        await write_audit_log(db=mock_db, action="SOME_ACTION")
        logged_object = mock_db.add.call_args[0][0]
        print(f"[DEBUG] logged_object.user_id    : {logged_object.user_id}")
        print(f"[DEBUG] logged_object.user_email : {logged_object.user_email}")
        print(f"[DEBUG] logged_object.resource   : {logged_object.resource}")
        print(f"[DEBUG] logged_object.detail     : {logged_object.detail}")
        print(f"[DEBUG] logged_object.ip_address : {logged_object.ip_address}")
        assert logged_object.user_id is None
        assert logged_object.user_email is None
        assert logged_object.resource is None
        assert logged_object.detail is None
        assert logged_object.ip_address is None
