"""
Tests for app/routers/areas.py

Mirrors the style of test_auth_router.py: endpoint functions are called
directly (no HTTP layer), the database is mocked via the `mock_db`
fixture, and geoalchemy2 / PostGIS calls are patched out so no real
database or spatial extension is needed.

Endpoint coverage:
  PUT    /api/v1/areas/users/{user_id}  – assign_user_area   (admin)
  DELETE /api/v1/areas/users/{user_id}  – remove_user_area   (admin)
  GET    /api/v1/areas/users/{user_id}  – get_user_area      (self or admin)
  POST   /api/v1/areas/check-point      – check_point        (authenticated)
  GET    /api/v1/areas/audit            – list_area_audit_logs (admin)
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from shapely.geometry import Polygon

from app.models.authorized_area import AuthorizedArea
from app.models.audit_log import AuditLog
from app.models.user import User, RoleEnum, AccountStatusEnum
from app.routers.areas import (
    assign_user_area,
    remove_user_area,
    get_user_area,
    check_point,
    list_area_audit_logs,
)
from app.schemas.area import AreaAssignSchema, PointCheckSchema
from tests.conftest import make_scalar_result

# ── Shared helpers ────────────────────────────────────────────────────────────

VALID_COORDS = [
    [72.5, 18.5],
    [73.0, 18.5],
    [73.0, 19.0],
    [72.5, 19.0],
]

VALID_SHAPELY_POLYGON = Polygon([
    (72.5, 18.5), (73.0, 18.5), (73.0, 19.0), (72.5, 19.0), (72.5, 18.5)
])


def fake_request(ip="127.0.0.1"):
    """Minimal stand-in for FastAPI's Request — just enough for get_ip()."""
    req = MagicMock()
    req.headers.get.return_value = None
    req.client.host = ip
    return req


def make_admin_user():
    return User(
        user_id=uuid.uuid4(),
        email="admin@example.com",
        user_name="adminuser",
        phone_no="0000000000",
        role=RoleEnum.admin,
        account_status=AccountStatusEnum.ACTIVATED,
    )


def make_viewer_user(user_id=None):
    return User(
        user_id=user_id or uuid.uuid4(),
        email="viewer@example.com",
        user_name="vieweruser",
        phone_no="1111111111",
        role=RoleEnum.viewer,
        account_status=AccountStatusEnum.ACTIVATED,
    )


def make_area(user_id, has_geometry=True):
    area = AuthorizedArea(user_id=user_id)
    area.authorized_area = MagicMock() if has_geometry else None
    return area


# ── assign_user_area ──────────────────────────────────────────────────────────

class TestAssignUserArea:
    async def test_invalid_uuid_raises_422(self, mock_db):
        print("\n[DEBUG] passing 'not-a-uuid' as user_id")
        with pytest.raises(HTTPException) as exc_info:
            await assign_user_area(
                user_id="not-a-uuid",
                payload=AreaAssignSchema(coordinates=VALID_COORDS),
                request=fake_request(),
                db=mock_db,
                admin=make_admin_user(),
            )
        print(f"[DEBUG] status_code={exc_info.value.status_code}, detail={exc_info.value.detail!r}")
        assert exc_info.value.status_code == 422

    async def test_user_not_found_raises_404(self, mock_db):
        target_id = str(uuid.uuid4())
        print(f"\n[DEBUG] target user_id={target_id}, db returns None for user lookup")
        # user lookup returns nothing; get_area_for_user never reached
        mock_db.execute.side_effect = [
            make_scalar_result(None),   # User lookup → not found
        ]
        with pytest.raises(HTTPException) as exc_info:
            await assign_user_area(
                user_id=target_id,
                payload=AreaAssignSchema(coordinates=VALID_COORDS),
                request=fake_request(),
                db=mock_db,
                admin=make_admin_user(),
            )
        print(f"[DEBUG] status_code={exc_info.value.status_code}, detail={exc_info.value.detail!r}")
        assert exc_info.value.status_code == 404

    async def test_creates_new_area_when_none_exists(self, mock_db):
        target_user = make_viewer_user()
        target_id = str(target_user.user_id)
        print(f"\n[DEBUG] target user exists, no existing area → should db.add() a new AuthorizedArea")
        mock_db.execute.side_effect = [
            make_scalar_result(target_user),   # User lookup → found
            make_scalar_result(None),           # get_area_for_user → no existing area
        ]
        mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(
            obj, "authorized_area", MagicMock()
        ))

        with (
            patch("app.routers.areas.from_shape", return_value="<wkb sentinel>"),
            patch("app.routers.areas.to_shape", return_value=VALID_SHAPELY_POLYGON),
        ):
            result = await assign_user_area(
                user_id=target_id,
                payload=AreaAssignSchema(coordinates=VALID_COORDS),
                request=fake_request(),
                db=mock_db,
                admin=make_admin_user(),
            )

        print(f"[DEBUG] result={result}")
        print(f"[DEBUG] db.add call count={mock_db.add.call_count}")
        assert result["user_id"] == target_id
        assert result["has_area"] is True
        # db.add called twice: once for the new AuthorizedArea, once for the audit log
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_awaited_once()

    async def test_updates_existing_area_without_extra_add(self, mock_db):
        target_user = make_viewer_user()
        target_id = str(target_user.user_id)
        existing_area = make_area(target_user.user_id)
        print(f"\n[DEBUG] existing area found → should update in-place, NOT call db.add for AuthorizedArea")
        mock_db.execute.side_effect = [
            make_scalar_result(target_user),
            make_scalar_result(existing_area),
        ]
        mock_db.refresh = AsyncMock(side_effect=lambda obj: None)
        existing_area.authorized_area = MagicMock()

        with (
            patch("app.routers.areas.from_shape", return_value="<wkb sentinel>"),
            patch("app.routers.areas.to_shape", return_value=VALID_SHAPELY_POLYGON),
        ):
            result = await assign_user_area(
                user_id=target_id,
                payload=AreaAssignSchema(coordinates=VALID_COORDS),
                request=fake_request(),
                db=mock_db,
                admin=make_admin_user(),
            )

        print(f"[DEBUG] result={result}")
        # Only the audit log triggers db.add; the area object is already tracked
        add_args = [call[0][0] for call in mock_db.add.call_args_list]
        print(f"[DEBUG] objects passed to db.add: {[type(o).__name__ for o in add_args]}")
        assert not any(isinstance(o, AuthorizedArea) for o in add_args)
        assert result["has_area"] is True


# ── remove_user_area ──────────────────────────────────────────────────────────

class TestRemoveUserArea:
    async def test_invalid_uuid_raises_422(self, mock_db):
        print("\n[DEBUG] passing 'bad-id' as user_id to remove")
        with pytest.raises(HTTPException) as exc_info:
            await remove_user_area(
                user_id="bad-id",
                request=fake_request(),
                db=mock_db,
                admin=make_admin_user(),
            )
        print(f"[DEBUG] status_code={exc_info.value.status_code}")
        assert exc_info.value.status_code == 422

    async def test_no_area_returns_message_without_commit(self, mock_db):
        target_id = str(uuid.uuid4())
        print(f"\n[DEBUG] user has no AuthorizedArea row at all → early return, no commit")
        mock_db.execute.return_value = make_scalar_result(None)

        result = await remove_user_area(
            user_id=target_id,
            request=fake_request(),
            db=mock_db,
            admin=make_admin_user(),
        )

        print(f"[DEBUG] result={result}")
        assert result == {"message": "User has no area assigned"}
        mock_db.commit.assert_not_awaited()

    async def test_area_row_exists_but_geometry_is_none_returns_message(self, mock_db):
        target_id = str(uuid.uuid4())
        area = make_area(uuid.UUID(target_id), has_geometry=False)
        print(f"\n[DEBUG] AuthorizedArea row exists but authorized_area=None → early return, no commit")
        mock_db.execute.return_value = make_scalar_result(area)

        result = await remove_user_area(
            user_id=target_id,
            request=fake_request(),
            db=mock_db,
            admin=make_admin_user(),
        )

        print(f"[DEBUG] result={result}")
        assert result == {"message": "User has no area assigned"}
        mock_db.commit.assert_not_awaited()

    async def test_successful_removal_nullifies_geometry_and_commits(self, mock_db):
        target_uid = uuid.uuid4()
        area = make_area(target_uid)
        print(f"\n[DEBUG] area exists with geometry → should set authorized_area=None and commit")
        print(f"[DEBUG] area.authorized_area before: {area.authorized_area}")
        mock_db.execute.return_value = make_scalar_result(area)

        result = await remove_user_area(
            user_id=str(target_uid),
            request=fake_request(),
            db=mock_db,
            admin=make_admin_user(),
        )

        print(f"[DEBUG] area.authorized_area after: {area.authorized_area}")
        print(f"[DEBUG] result={result}")
        assert area.authorized_area is None
        assert "removed" in result["message"]
        mock_db.commit.assert_awaited_once()


# ── get_user_area ─────────────────────────────────────────────────────────────

class TestGetUserArea:
    async def test_invalid_uuid_raises_422(self, mock_db):
        viewer = make_viewer_user()
        print("\n[DEBUG] passing 'xyz' as user_id to get_user_area")
        with pytest.raises(HTTPException) as exc_info:
            await get_user_area(user_id="xyz", db=mock_db, user=viewer)
        print(f"[DEBUG] status_code={exc_info.value.status_code}")
        assert exc_info.value.status_code == 422

    async def test_viewer_accessing_other_user_area_is_forbidden(self, mock_db):
        viewer = make_viewer_user()
        other_id = str(uuid.uuid4())
        print(f"\n[DEBUG] viewer user_id={viewer.user_id}, trying to access area for other_id={other_id}")
        with pytest.raises(HTTPException) as exc_info:
            await get_user_area(user_id=other_id, db=mock_db, user=viewer)
        print(f"[DEBUG] status_code={exc_info.value.status_code}, detail={exc_info.value.detail!r}")
        assert exc_info.value.status_code == 403

    async def test_viewer_can_access_own_area(self, mock_db):
        viewer = make_viewer_user()
        area = make_area(viewer.user_id, has_geometry=False)
        print(f"\n[DEBUG] viewer accessing their own area (has_geometry=False)")
        mock_db.execute.return_value = make_scalar_result(area)

        with patch("app.routers.areas.to_shape", return_value=VALID_SHAPELY_POLYGON):
            result = await get_user_area(user_id=str(viewer.user_id), db=mock_db, user=viewer)

        print(f"[DEBUG] result={result}")
        assert result["user_id"] == str(viewer.user_id)
        assert result["has_area"] is False

    async def test_admin_can_access_any_user_area(self, mock_db):
        admin = make_admin_user()
        target_id = str(uuid.uuid4())
        area = make_area(uuid.UUID(target_id))
        print(f"\n[DEBUG] admin accessing area for target_id={target_id}")
        mock_db.execute.return_value = make_scalar_result(area)

        with patch("app.routers.areas.to_shape", return_value=VALID_SHAPELY_POLYGON):
            result = await get_user_area(user_id=target_id, db=mock_db, user=admin)

        print(f"[DEBUG] result={result}")
        assert result["user_id"] == target_id
        assert result["has_area"] is True
        assert result["area"] is not None

    async def test_user_with_no_area_row_returns_has_area_false(self, mock_db):
        viewer = make_viewer_user()
        print(f"\n[DEBUG] no AuthorizedArea row at all → has_area=False, area=None")
        mock_db.execute.return_value = make_scalar_result(None)

        result = await get_user_area(user_id=str(viewer.user_id), db=mock_db, user=viewer)

        print(f"[DEBUG] result={result}")
        assert result["has_area"] is False
        assert result["area"] is None


# ── check_point ───────────────────────────────────────────────────────────────

class TestCheckPoint:
    async def test_user_with_no_area_raises_403(self, mock_db):
        user = make_viewer_user()
        print(f"\n[DEBUG] user has no area → check-point should raise 403")
        mock_db.execute.return_value = make_scalar_result(None)

        with pytest.raises(HTTPException) as exc_info:
            await check_point(
                payload=PointCheckSchema(longitude=72.88, latitude=19.08),
                request=fake_request(),
                db=mock_db,
                user=user,
            )

        print(f"[DEBUG] status_code={exc_info.value.status_code}, detail={exc_info.value.detail!r}")
        assert exc_info.value.status_code == 403
        mock_db.commit.assert_awaited_once()  # audit log commit still happens

    async def test_user_with_area_row_but_null_geometry_raises_403(self, mock_db):
        user = make_viewer_user()
        area = make_area(user.user_id, has_geometry=False)
        print(f"\n[DEBUG] area row exists but authorized_area=None → 403")
        mock_db.execute.return_value = make_scalar_result(area)

        with pytest.raises(HTTPException) as exc_info:
            await check_point(
                payload=PointCheckSchema(longitude=72.88, latitude=19.08),
                request=fake_request(),
                db=mock_db,
                user=user,
            )

        print(f"[DEBUG] status_code={exc_info.value.status_code}")
        assert exc_info.value.status_code == 403

    async def test_point_inside_area_returns_true(self, mock_db):
        user = make_viewer_user()
        area = make_area(user.user_id)

        st_contains_result = MagicMock()
        st_contains_result.scalar.return_value = True

        print(f"\n[DEBUG] ST_Contains returns True → inside=True")
        mock_db.execute.side_effect = [
            make_scalar_result(area),    # get_area_for_user
            st_contains_result,           # ST_Contains query
        ]

        result = await check_point(
            payload=PointCheckSchema(longitude=72.88, latitude=19.08),
            request=fake_request(),
            db=mock_db,
            user=user,
        )

        print(f"[DEBUG] result={result}")
        assert result == {"inside": True}
        mock_db.commit.assert_awaited_once()

    async def test_point_outside_area_returns_false(self, mock_db):
        user = make_viewer_user()
        area = make_area(user.user_id)

        st_contains_result = MagicMock()
        st_contains_result.scalar.return_value = False

        print(f"\n[DEBUG] ST_Contains returns False → inside=False")
        mock_db.execute.side_effect = [
            make_scalar_result(area),
            st_contains_result,
        ]

        result = await check_point(
            payload=PointCheckSchema(longitude=0.0, latitude=0.0),
            request=fake_request(),
            db=mock_db,
            user=user,
        )

        print(f"[DEBUG] result={result}")
        assert result == {"inside": False}

    async def test_check_point_writes_audit_log(self, mock_db):
        user = make_viewer_user()
        area = make_area(user.user_id)

        st_contains_result = MagicMock()
        st_contains_result.scalar.return_value = True

        mock_db.execute.side_effect = [
            make_scalar_result(area),
            st_contains_result,
        ]

        await check_point(
            payload=PointCheckSchema(longitude=72.88, latitude=19.08),
            request=fake_request(),
            db=mock_db,
            user=user,
        )

        # Audit log is written via db.add
        add_args = [call[0][0] for call in mock_db.add.call_args_list]
        print(f"\n[DEBUG] objects added to db: {[type(o).__name__ for o in add_args]}")
        assert any(isinstance(o, AuditLog) for o in add_args)


# ── list_area_audit_logs ──────────────────────────────────────────────────────

class TestListAreaAuditLogs:
    async def test_returns_list_of_audit_logs(self, mock_db):
        log1 = AuditLog(action="CHECK_POINT", success=True)
        log2 = AuditLog(action="ASSIGN_USER_AREA", success=True)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [log1, log2]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        mock_db.execute.return_value = execute_result

        print(f"\n[DEBUG] db returns 2 AuditLog rows")
        result = await list_area_audit_logs(
            db=mock_db,
            _admin=make_admin_user(),
            limit=50,
            offset=0,
        )

        print(f"[DEBUG] result count={len(result)}")
        print(f"[DEBUG] actions={[r.action for r in result]}")
        assert len(result) == 2
        assert result[0].action == "CHECK_POINT"

    async def test_empty_audit_log_returns_empty_list(self, mock_db):
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        mock_db.execute.return_value = execute_result

        print(f"\n[DEBUG] db returns empty audit log")
        result = await list_area_audit_logs(
            db=mock_db,
            _admin=make_admin_user(),
            limit=50,
            offset=0,
        )

        print(f"[DEBUG] result={result}")
        assert result == []

    async def test_pagination_params_are_forwarded(self, mock_db):
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        mock_db.execute.return_value = execute_result

        print(f"\n[DEBUG] calling with limit=10, offset=20 — verifying db.execute is called once")
        await list_area_audit_logs(
            db=mock_db,
            _admin=make_admin_user(),
            limit=10,
            offset=20,
        )

        # db.execute must be called exactly once (for the paginated query)
        assert mock_db.execute.call_count == 1
