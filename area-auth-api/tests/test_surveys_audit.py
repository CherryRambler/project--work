"""
Tests for the enhanced survey record audit logging.

Verifies:
  - survey_record_id is stored on every audit log entry
  - change_type is classified correctly per endpoint
  - changes JSONB captures old/new values
  - existing write_audit_log() callers without new params still work
  - DELETE writes the audit log before deleting the record
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from shapely.geometry import Polygon

from app.core.audit_logger import write_audit_log
from app.models.audit_log import AuditLog
from app.models.survey_record import SurveyRecord
from app.models.user import AccountStatusEnum, RoleEnum, User
from app.routers.surveys import (
    admin_update_survey_record,
    create_survey_record,
    delete_survey_record,
    verify_survey_record,
)
from app.schemas.survey import (
    SurveyAdminUpdateSchema,
    SurveyCreateSchema,
    SurveyVerifySchema,
)

# ── Shared helpers ────────────────────────────────────────────────────────────

VALID_COORDS = [
    [72.5, 18.5], [73.0, 18.5], [73.0, 19.0], [72.5, 19.0],
]
VALID_POLYGON = Polygon([
    (72.5, 18.5), (73.0, 18.5), (73.0, 19.0), (72.5, 19.0), (72.5, 18.5)
])


def fake_request():
    req = MagicMock()
    req.headers.get.return_value = None
    req.client.host = "127.0.0.1"
    return req


def make_scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def make_admin():
    return User(
        user_id=uuid.uuid4(), email="admin@test.com", user_name="admin",
        phone_no="0000000000", role=RoleEnum.admin,
        account_status=AccountStatusEnum.ACTIVATED,
    )


def make_viewer():
    return User(
        user_id=uuid.uuid4(), email="viewer@test.com", user_name="viewer",
        phone_no="1111111111", role=RoleEnum.viewer,
        account_status=AccountStatusEnum.ACTIVATED,
    )


def make_survey(user_id=None, verified=False):
    """Build a SurveyRecord with a pre-assigned id so mocked flush works."""
    sr = SurveyRecord(
        user_id=user_id or uuid.uuid4(),
        village="Andheri",
        plot="Plot-1",
        verified_status=verified,
    )
    sr.id = uuid.uuid4()          # assign id upfront — flush is mocked
    sr.geometry = MagicMock()
    sr.timestamp = datetime.now(timezone.utc)
    return sr


def make_mock_db(added_objects=None):
    """
    Build a mock AsyncSession where:
    - add() collects objects and assigns a UUID to any SurveyRecord missing one
    - flush() is a no-op async (the UUID was already assigned in make_survey)
    - refresh() stamps timestamp on the object
    """
    if added_objects is None:
        added_objects = []

    mock_db = AsyncMock()

    def _add(obj):
        # Ensure SurveyRecord always has an id even without a real flush
        if isinstance(obj, SurveyRecord) and obj.id is None:
            obj.id = uuid.uuid4()
        added_objects.append(obj)

    mock_db.add = MagicMock(side_effect=_add)
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(
        side_effect=lambda obj: setattr(obj, "timestamp", datetime.now(timezone.utc))
        if not hasattr(obj, "timestamp") or obj.timestamp is None else None
    )
    return mock_db


# ── 1. Backward compatibility ─────────────────────────────────────────────────

class TestAuditLoggerBackwardCompat:
    async def test_existing_callers_work_without_new_params(self):
        """
        write_audit_log() called without the new params must still create
        a valid AuditLog row with survey_record_id / change_type / changes as NULL.
        """
        db = AsyncMock()
        db.add = MagicMock()

        await write_audit_log(
            db=db,
            action="LOGIN_SUCCESS",
            user_id=uuid.uuid4(),
            user_email="user@test.com",
            detail="Login from web",
            ip_address="127.0.0.1",
        )

        db.add.assert_called_once()
        log: AuditLog = db.add.call_args[0][0]
        assert isinstance(log, AuditLog)
        assert log.action == "LOGIN_SUCCESS"
        assert log.survey_record_id is None
        assert log.change_type is None
        assert log.changes is None
        print(f"\n[DEBUG] backward-compat log: action={log.action}, "
              f"survey_record_id={log.survey_record_id}, change_type={log.change_type}")

    async def test_new_params_stored_correctly(self):
        """New survey params are persisted when provided."""
        db = AsyncMock()
        db.add = MagicMock()
        survey_id = uuid.uuid4()

        await write_audit_log(
            db=db,
            action="SURVEY_VERIFIED",
            change_type="VERIFY",
            user_id=uuid.uuid4(),
            user_email="viewer@test.com",
            survey_record_id=survey_id,
            changes={"field": "verified_status", "old": False, "new": True},
            detail="verified_status changed from False to True",
        )

        log: AuditLog = db.add.call_args[0][0]
        assert log.change_type == "VERIFY"
        assert log.survey_record_id == survey_id
        assert log.changes == {"field": "verified_status", "old": False, "new": True}
        print(f"\n[DEBUG] survey audit log: change_type={log.change_type}, "
              f"survey_record_id={log.survey_record_id}, changes={log.changes}")


# ── 2. create_survey_record audit metadata ────────────────────────────────────

class TestCreateSurveyAudit:
    async def test_create_writes_audit_with_survey_record_id(self):
        admin = make_admin()
        viewer = make_viewer()
        added_objects = []
        mock_db = make_mock_db(added_objects)
        mock_db.execute.return_value = make_scalar_result(viewer)

        with (
            patch("app.routers.surveys.from_shape", return_value=MagicMock()),
            patch("app.routers.surveys.to_shape", return_value=VALID_POLYGON),
        ):
            await create_survey_record(
                payload=SurveyCreateSchema(
                    user_id=str(viewer.user_id),
                    village="Andheri",
                    plot="Plot-42",
                    coordinates=VALID_COORDS,
                ),
                request=fake_request(),
                db=mock_db,
                admin=admin,
            )

        audit_logs = [o for o in added_objects if isinstance(o, AuditLog)]
        survey_records = [o for o in added_objects if isinstance(o, SurveyRecord)]

        assert len(audit_logs) == 1
        assert len(survey_records) == 1

        log = audit_logs[0]
        record = survey_records[0]

        print(f"\n[DEBUG] create audit: action={log.action}, "
              f"change_type={log.change_type}, survey_record_id={log.survey_record_id}")
        print(f"[DEBUG] survey record id: {record.id}")
        print(f"[DEBUG] changes: {log.changes}")

        assert log.action == "SURVEY_CREATED"
        assert log.change_type == "CREATE"
        # survey_record_id must match the SurveyRecord that was created
        assert log.survey_record_id is not None
        assert log.survey_record_id == record.id
        assert log.changes is not None
        assert "new" in log.changes
        assert log.changes["new"]["village"] == "Andheri"
        assert log.changes["new"]["verified_status"] is False

    async def test_create_audit_email_matches_admin(self):
        admin = make_admin()
        viewer = make_viewer()
        added_objects = []
        mock_db = make_mock_db(added_objects)
        mock_db.execute.return_value = make_scalar_result(viewer)

        with (
            patch("app.routers.surveys.from_shape", return_value=MagicMock()),
            patch("app.routers.surveys.to_shape", return_value=VALID_POLYGON),
        ):
            await create_survey_record(
                payload=SurveyCreateSchema(
                    user_id=str(viewer.user_id),
                    village="Andheri",
                    plot="Plot-42",
                    coordinates=VALID_COORDS,
                ),
                request=fake_request(),
                db=mock_db,
                admin=admin,
            )

        log = next(o for o in added_objects if isinstance(o, AuditLog))
        print(f"\n[DEBUG] audit actor: user_id={log.user_id}, email={log.user_email}")
        assert log.user_id == admin.user_id
        assert log.user_email == admin.email


# ── 3. verify writes correct change_type and changes ─────────────────────────

class TestVerifySurveyAudit:
    async def test_verify_true_writes_verify_change_type(self):
        user = make_viewer()
        survey = make_survey(user_id=user.user_id, verified=False)
        added_objects = []
        mock_db = make_mock_db(added_objects)
        mock_db.execute.return_value = make_scalar_result(survey)

        with patch("app.routers.surveys.to_shape", return_value=VALID_POLYGON):
            await verify_survey_record(
                record_id=str(survey.id),
                payload=SurveyVerifySchema(verified_status=True),
                request=fake_request(),
                db=mock_db,
                user=user,
            )

        log = next(o for o in added_objects if isinstance(o, AuditLog))
        print(f"\n[DEBUG] verify audit: change_type={log.change_type}, changes={log.changes}")

        assert log.action == "SURVEY_VERIFIED"
        assert log.change_type == "VERIFY"
        assert log.survey_record_id == survey.id
        assert log.changes["field"] == "verified_status"
        assert log.changes["old"] is False
        assert log.changes["new"] is True

    async def test_toggle_back_to_false_still_writes_audit(self):
        user = make_viewer()
        survey = make_survey(user_id=user.user_id, verified=True)
        added_objects = []
        mock_db = make_mock_db(added_objects)
        mock_db.execute.return_value = make_scalar_result(survey)

        with patch("app.routers.surveys.to_shape", return_value=VALID_POLYGON):
            await verify_survey_record(
                record_id=str(survey.id),
                payload=SurveyVerifySchema(verified_status=False),
                request=fake_request(),
                db=mock_db,
                user=user,
            )

        log = next(o for o in added_objects if isinstance(o, AuditLog))
        print(f"\n[DEBUG] un-verify audit: changes={log.changes}")
        assert log.changes["old"] is True
        assert log.changes["new"] is False

    async def test_viewer_cannot_verify_other_users_record(self):
        viewer = make_viewer()
        other_survey = make_survey(user_id=uuid.uuid4())  # different user
        added_objects = []
        mock_db = make_mock_db(added_objects)
        mock_db.execute.return_value = make_scalar_result(other_survey)

        with pytest.raises(HTTPException) as exc_info:
            await verify_survey_record(
                record_id=str(other_survey.id),
                payload=SurveyVerifySchema(verified_status=True),
                request=fake_request(),
                db=mock_db,
                user=viewer,
            )

        print(f"\n[DEBUG] access denied: status={exc_info.value.status_code}")
        assert exc_info.value.status_code == 403
        # No audit log should have been written
        assert not any(isinstance(o, AuditLog) for o in added_objects)


# ── 4. admin_update change_type classification ────────────────────────────────

class TestAdminUpdateChangeType:
    async def test_village_change_classified_as_update(self):
        admin = make_admin()
        survey = make_survey()
        added_objects = []
        mock_db = make_mock_db(added_objects)
        mock_db.execute.return_value = make_scalar_result(survey)

        with patch("app.routers.surveys.to_shape", return_value=VALID_POLYGON):
            await admin_update_survey_record(
                record_id=str(survey.id),
                payload=SurveyAdminUpdateSchema(village="Borivali"),
                request=fake_request(),
                db=mock_db,
                admin=admin,
            )

        log = next(o for o in added_objects if isinstance(o, AuditLog))
        print(f"\n[DEBUG] village update: change_type={log.change_type}, changes={log.changes}")
        assert log.change_type == "UPDATE"
        assert log.changes["old"]["village"] == "Andheri"
        assert log.changes["new"]["village"] == "Borivali"
        assert log.survey_record_id == survey.id

    async def test_verified_status_only_classified_as_status_change(self):
        admin = make_admin()
        survey = make_survey(verified=False)
        added_objects = []
        mock_db = make_mock_db(added_objects)
        mock_db.execute.return_value = make_scalar_result(survey)

        with patch("app.routers.surveys.to_shape", return_value=VALID_POLYGON):
            await admin_update_survey_record(
                record_id=str(survey.id),
                payload=SurveyAdminUpdateSchema(verified_status=True),
                request=fake_request(),
                db=mock_db,
                admin=admin,
            )

        log = next(o for o in added_objects if isinstance(o, AuditLog))
        print(f"\n[DEBUG] status change: change_type={log.change_type}, changes={log.changes}")
        assert log.change_type == "STATUS_CHANGE"
        assert log.changes["old"]["verified_status"] is False
        assert log.changes["new"]["verified_status"] is True

    async def test_reassignment_classified_as_assign(self):
        admin = make_admin()
        survey = make_survey()
        new_user = make_viewer()
        added_objects = []
        mock_db = make_mock_db(added_objects)
        mock_db.execute.side_effect = [
            make_scalar_result(survey),    # get record
            make_scalar_result(new_user),  # new user lookup
        ]

        with patch("app.routers.surveys.to_shape", return_value=VALID_POLYGON):
            await admin_update_survey_record(
                record_id=str(survey.id),
                payload=SurveyAdminUpdateSchema(user_id=str(new_user.user_id)),
                request=fake_request(),
                db=mock_db,
                admin=admin,
            )

        log = next(o for o in added_objects if isinstance(o, AuditLog))
        print(f"\n[DEBUG] reassignment: change_type={log.change_type}, changes={log.changes}")
        assert log.change_type == "ASSIGN"
        assert "user_id" in log.changes["fields"]

    async def test_no_fields_raises_400(self):
        admin = make_admin()
        survey = make_survey()
        added_objects = []
        mock_db = make_mock_db(added_objects)
        mock_db.execute.return_value = make_scalar_result(survey)

        with pytest.raises(HTTPException) as exc_info:
            await admin_update_survey_record(
                record_id=str(survey.id),
                payload=SurveyAdminUpdateSchema(),  # nothing provided
                request=fake_request(),
                db=mock_db,
                admin=admin,
            )

        print(f"\n[DEBUG] no fields: status={exc_info.value.status_code}")
        assert exc_info.value.status_code == 400
        assert not any(isinstance(o, AuditLog) for o in added_objects)

    async def test_multiple_fields_captured_in_changes(self):
        admin = make_admin()
        survey = make_survey()
        added_objects = []
        mock_db = make_mock_db(added_objects)
        mock_db.execute.return_value = make_scalar_result(survey)

        with patch("app.routers.surveys.to_shape", return_value=VALID_POLYGON):
            await admin_update_survey_record(
                record_id=str(survey.id),
                payload=SurveyAdminUpdateSchema(village="Borivali", plot="Plot-99"),
                request=fake_request(),
                db=mock_db,
                admin=admin,
            )

        log = next(o for o in added_objects if isinstance(o, AuditLog))
        print(f"\n[DEBUG] multi-field update: changes={log.changes}")
        assert "village" in log.changes["fields"]
        assert "plot" in log.changes["fields"]
        assert log.changes["old"]["village"] == "Andheri"
        assert log.changes["old"]["plot"] == "Plot-1"
        assert log.changes["new"]["village"] == "Borivali"
        assert log.changes["new"]["plot"] == "Plot-99"


# ── 5. delete writes audit BEFORE deleting the record ────────────────────────

class TestDeleteSurveyAudit:
    async def test_delete_audit_log_written_before_delete(self):
        """
        The audit log must be flushed BEFORE db.delete(record) is called,
        so the survey_record_id FK is still valid at flush time.
        """
        admin = make_admin()
        survey = make_survey()
        added_objects = []
        call_order = []

        mock_db = AsyncMock()

        def _add(obj):
            added_objects.append(obj)
            call_order.append("add")

        mock_db.add = MagicMock(side_effect=_add)
        mock_db.flush = AsyncMock(side_effect=lambda: call_order.append("flush"))
        mock_db.delete = AsyncMock(side_effect=lambda obj: call_order.append("delete"))
        mock_db.commit = AsyncMock(side_effect=lambda: call_order.append("commit"))
        mock_db.execute.return_value = make_scalar_result(survey)

        result = await delete_survey_record(
            record_id=str(survey.id),
            request=fake_request(),
            db=mock_db,
            admin=admin,
        )

        print(f"\n[DEBUG] delete call order: {call_order}")
        print(f"[DEBUG] result: {result}")

        # add (log) → flush → delete → commit
        assert call_order.index("add") < call_order.index("flush")
        assert call_order.index("flush") < call_order.index("delete")

        log = next(o for o in added_objects if isinstance(o, AuditLog))
        print(f"[DEBUG] delete audit: action={log.action}, change_type={log.change_type}")
        print(f"[DEBUG] snapshot: {log.changes}")

        assert log.action == "SURVEY_DELETED"
        assert log.change_type == "DELETE"
        assert log.survey_record_id == survey.id
        assert "snapshot" in log.changes
        assert log.changes["snapshot"]["village"] == "Andheri"
        assert log.changes["snapshot"]["verified_status"] is False

    async def test_delete_nonexistent_record_raises_404(self):
        admin = make_admin()
        mock_db = AsyncMock()
        mock_db.execute.return_value = make_scalar_result(None)

        with pytest.raises(HTTPException) as exc_info:
            await delete_survey_record(
                record_id=str(uuid.uuid4()),
                request=fake_request(),
                db=mock_db,
                admin=admin,
            )

        print(f"\n[DEBUG] delete nonexistent: status={exc_info.value.status_code}")
        assert exc_info.value.status_code == 404