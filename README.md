# Area Authorization System — Project Documentation

## 1. Project Overview

This project implements a **role-based access control (RBAC) system** for assigning and managing geographic "authorized areas" to users. It consists of:

- A single **FastAPI backend application** (`combined-api`) handling authentication, user management, and geographic area authorization
- A **PostgreSQL + PostGIS** database for storing users, sessions, audit logs, and geospatial area data
- A **React (Vite) frontend** for registration, login, and viewing/managing assigned areas

The system supports two user roles: **Admin** and **Viewer**.

---

## 2. Architecture

The backend runs as a single FastAPI application on one port, backed by one PostgreSQL database (`auth_db`), with one shared `.env` configuration and one JWT signing secret used consistently across all authentication and authorization checks.

**Folder structure (`combined-api`):**
```
combined-api/
├── .env
├── requirements.txt
├── pytest.ini
├── requirements-test.txt
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   ├── audit_logger.py
│   │   └── audit_actions.py
│   ├── db/
│   │   └── session.py
│   ├── models/
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── authorized_area.py
│   │   └── audit_log.py
│   ├── schemas/
│   │   ├── auth.py
│   │   └── area.py
│   └── routers/
│       ├── auth.py
│       └── areas.py
└── tests/
    ├── conftest.py
    ├── test_security.py
    ├── test_schemas.py
    ├── test_audit_logger.py
    └── test_auth_router.py
```

`app/main.py` mounts both the `auth` and `areas` routers on a single `FastAPI()` instance, with CORS middleware configured to allow the frontend's origin(s).

---

## 3. Database Schema

### 3.0 Entity-Relationship Diagram

![Entity-Relationship Diagram](docs\er-diagram.png)

The diagram above shows the four core tables and their relationships:
- **`users` → `audit_logs`** (1-to-N): one user can generate many audit log entries.
- **`users` → `authorized_areas`** (1-to-1): each user has at most one assigned authorized area, enforced via a foreign key on `authorized_areas.user_id` referencing `users.user_id` (`ON DELETE CASCADE`).
- **`users` → `user_sessions`** (1-to-N): one user can have many active login sessions (one per device/login).

### 3.1 `users` table
| Column | Type | Notes |
|---|---|---|
| user_id | UUID (PK) | |
| user_name | String, unique | |
| email | String, unique | |
| phone_no | String, unique | |
| role | Enum: `admin`, `viewer` | |
| hashed_password | String | |
| account_status | Enum: `ACTIVATED`, `DEACTIVATED` | Replaces original `is_active` boolean — admin-controlled |
| created_at | Timestamp | |
| failed_login_attempts | Integer | |
| locked_until | Timestamp (nullable) | |

### 3.2 `authorized_areas` table
| Column | Type | Notes |
|---|---|---|
| user_id | UUID (PK, FK → users.user_id, ON DELETE CASCADE) | One area per user |
| authorized_area | Geometry(POLYGON, 4326) | PostGIS polygon |
| created_at | Timestamptz | |
| updated_at | Timestamptz | |

### 3.3 `audit_logs` table
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (nullable, FK → users.user_id, ON DELETE SET NULL) | |
| user_email | String (nullable) | |
| action | String(100) | e.g. LOGIN_SUCCESS, ASSIGN_USER_AREA |
| resource | String(200) | |
| detail | Text | |
| ip_address | String(50) | |
| success | Boolean | |
| created_at | Timestamptz | |

### 3.4 `user_sessions` table
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID, FK → users.user_id (no ON DELETE rule) | |
| refresh_token | String, unique | |
| platform | String(20) | |
| ip_address | String(50) | |
| is_active | Boolean | |
| created_at | Timestamptz | |
| last_used_at | Timestamptz | |
| expires_at | Timestamptz | |

Stores refresh tokens, platform, IP, and expiry per login session, supporting logout / logout-all / session listing.

**Note:** the `user_sessions` foreign key has no `ON DELETE` cascade rule, meaning deleting a user who still has session rows will fail with a FK violation. Session rows must be deleted or the FK must be changed to `ON DELETE CASCADE` before a user can be deleted.

### 3.5 Indexing

| Table | Index | Purpose |
|---|---|---|
| `users` | Unique index on `email` | Login lookup, registration uniqueness |
| `users` | Unique index on `user_name` | Registration uniqueness |
| `users` | Unique index on `phone_no` | Registration uniqueness |
| `authorized_areas` | GIST index on `authorized_area` | Efficient `ST_Contains` spatial queries in point-check |
| `audit_logs` | B-tree index on `created_at DESC` | Efficient sorting in audit log listing |
| `user_sessions` | Unique index on `refresh_token` | Login/refresh token lookup |
| `user_sessions` | Composite index on `(user_id, is_active)` | Session listing, logout-all |

All indexes were verified using `EXPLAIN ANALYZE` and `pg_stat_user_indexes`. No structural schema changes were required to support indexing — all indexed columns already existed and matched actual query filter/sort/join patterns.

---

## 4. Authentication & Authorization

- **JWT-based authentication** using `python-jose`, with separate secrets for access and refresh tokens (`ACCESS_TOKEN_SECRET`, `REFRESH_TOKEN_SECRET`).
- Access tokens embed: `sub` (user_id), `type`, `role`, `is_active`, `exp`.
- **`get_current_user`** dependency decodes the token, re-fetches the user from the database on **every request**, and rejects the request immediately if `account_status != ACTIVATED` — meaning admin deactivation takes effect instantly, even on a still-valid token, not just on the next login attempt.
- **`require_role(*roles)`** dependency factory enforces role-based access on specific endpoints.
- **Account lockout**: 5 failed login attempts locks the account for 5 minutes (`locked_until`), with an admin-only `/unlock/{user_id}` endpoint to manually clear it.

### 4.1 Refresh Token Rotation

The `/refresh` endpoint implements **refresh token rotation** — every time a refresh token is used, the old token is invalidated and a brand new access + refresh token pair is issued. This means:

- Each refresh token is single-use; it cannot be reused after rotation.
- The response from `/refresh` now returns **both** `access_token` and `refresh_token` (previously only returned `access_token`).
- **Reuse detection:** if a token that was already rotated away from is presented again (e.g. by a stolen copy), the endpoint detects this and **revokes all active sessions for that user** as a precaution, logging an audit entry for the event.
- The frontend's `AuthContext.jsx` was updated to store the newly issued refresh token from every `/refresh` response, replacing the old one in `localStorage`.

### 4.2 Role Permissions Summary

| Action | Admin | Viewer |
|---|---|---|
| Register / Login | ✅ | ✅ |
| View own profile (`/me`) | ✅ | ✅ |
| Change own password / update phone | ✅ | ✅ |
| View own assigned area | ✅ | ✅ |
| Run point-in-area check | ✅ | ✅ |
| View another user's assigned area | ✅ | ❌ |
| Assign an area to any user | ✅ | ❌ |
| Update an area for any user | ✅ | ❌ |
| Assign or update their own area | ✅ | ❌ |
| Delete any user's area | ✅ | ❌ |
| Delete their own area | ✅ | ❌ |
| Activate / deactivate other accounts | ✅ | ❌ |
| Unlock locked accounts | ✅ | ❌ |
| View audit logs | ✅ | ❌ |

**Note:** Viewers are strictly read-only with respect to area data. An assigned area represents an authorization boundary that only an Admin can create, modify, or remove — including for the viewer themselves. Viewers can see their own assignment and run point-in-polygon checks, but have no ability to change area data.

---

## 5. API Endpoints

### 5.1 Auth (`/api/v1/auth`)
| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/register` | Public | Create account (role specified at registration: admin or viewer) |
| POST | `/login` | Public | Authenticate, returns access + refresh tokens |
| POST | `/refresh` | Public (valid refresh token) | Issue new access + refresh token pair (token rotation) |
| POST | `/logout` | Authenticated | Invalidate one session |
| POST | `/logout-all` | Authenticated | Invalidate all sessions |
| GET | `/sessions` | Authenticated | List active sessions |
| GET | `/me` | Authenticated | Get own profile |
| PUT | `/me` | Authenticated | Update own phone number |
| PUT | `/me/password` | Authenticated | Change own password |
| POST | `/unlock/{user_id}` | Admin only | Clear failed-login lockout |
| PUT | `/users/{user_id}/status` | Admin only | Activate/deactivate another user's account |

### 5.2 Areas (`/api/v1/areas`)
| Method | Path | Access | Purpose |
|---|---|---|---|
| PUT | `/users/{user_id}` | Admin only | Assign or update a user's authorized area |
| DELETE | `/users/{user_id}` | Admin only | Remove a user's authorized area |
| GET | `/users/{user_id}` | Self or Admin | View own area (viewer) or any user's area (admin) |
| POST | `/check-point` | Authenticated | Check if a coordinate falls inside the caller's own assigned area |
| GET | `/audit` | Admin only | View paginated audit log entries |

---

## 6. Key Bugs Found and Fixed

| # | Issue | Root Cause | Fix |
|---|---|---|---|
| 1 | PostGIS extension missing | Not installed alongside PostgreSQL | Installed PostGIS bundle matching PG version via Stack Builder / OSGeo installer |
| 2 | Double `Bearer Bearer` in Authorization header | Swagger UI auto-prepends `Bearer`; pasting it again duplicated it | Paste raw token only into Authorize popup |
| 3 | New registrations always saved as `viewer` | `role` hardcoded in register endpoint, ignoring submitted value | Read and validate `data.role` against `RoleEnum` |
| 4 | `401 Invalid or expired token` | Misread/misconfigured `ACCESS_TOKEN_SECRET`, or stale environment variable overriding `.env` | Verified secret loading with diagnostic print statements, corrected configuration |
| 5 | `422 Unprocessable Entity` on area assignment | Coordinates sent with an extra nesting level (`[[[...]]]` instead of `[[...]]`) | Corrected request body shape |
| 6 | `relation does not exist` (multiple tables) | Tables defined in SQLAlchemy models but never created in the actual database | Manually ran `CREATE TABLE` (and later `Base.metadata.create_all`) |
| 7 | `TypeError: unsupported operand type(s) for |` | `X | None` union syntax used on Python 3.9 (requires 3.10+) | Replaced with `Optional[X]` |
| 8 | Frontend dashboard blank after login | Missing `import { MapContainer, ... } from "react-leaflet"` in `AreaMap.jsx` | Restored the import statement |
| 9 | Map tiles never rendered (polygon visible, background blank) | Network's authenticating proxy blocked external tile requests (`407 Proxy Authentication Required`) | Temporarily replaced with coordinate table; later resolved by switching to Esri ArcGIS tile provider |
| 10 | Dashboard always showed "No area assigned" despite successful DB save | Frontend expected an array of areas; backend returned a single `{user_id, has_area, area}` object | Normalized backend response into a one-item array in `AuthContext` |
| 11 | Delete button visible to viewers | No role check in `AreaCard` component | Added `isAdmin` prop to conditionally render the Delete button; backend already enforced `require_role("admin")` independently |
| 12 | Editor role redundant | Editor had admin-level UI visibility but no distinct backend permissions (identical to viewer in practice) | Removed `editor` from `RoleEnum` and all role checks across frontend and backend |
| 13 | Duplicate database indexes | Manually created indexes overlapped with indexes SQLAlchemy auto-created from `unique=True` model fields | Identified and dropped redundant indexes via `\d <table>` inspection |
| 14 | `ModuleNotFoundError: No module named 'app'` / `'tests'` running pytest | Test folder naming mismatch and cross-file import assumptions | Defined shared test helpers locally within each test file so files run independently |
| 15 | `column users.is_active does not exist` on login | `user.py` model still had an `is_active` column after the migration to `account_status`; DB and model out of sync | Removed the leftover `is_active` column from the SQLAlchemy model to match the actual database schema |
| 16 | `GET /api/v1/auth/users/{id}` returning 404 for area requests | Frontend `config.js` was simplified to a single prefix (`/api/v1/auth`); all area API calls were incorrectly routed to the auth prefix instead of `/api/v1/areas` | Restored two separate prefix constants (`AUTH_API_PREFIX`, `AREA_API_PREFIX`) in `config.js`; updated `auth.js` to use the correct constant per call group |
| 17 | `401 Invalid token` / `404 Session not found` when calling `/refresh` and `/logout` | Access token was mistakenly passed in the request body instead of the refresh token; the two tokens have different `type` claims (`"access"` vs `"refresh"`) | Clarified token usage: access token belongs only in the `Authorization: Bearer` header; refresh token (with `"type": "refresh"`) belongs in the request body |
| 18 | `PUT /areas/users/{id}` and `DELETE /areas/users/{id}` incorrectly allowed viewers to manage their own area | `areas.py` was updated to use `get_current_user` + a self-check instead of `require_role("admin")`, deviating from the intended design | Reverted both endpoints back to `require_role("admin")`; viewers must never create, update, or delete area assignments — only admins control area data |

---

## 7. Frontend Implementation Notes

- **Stack:** React + Vite, plain CSS (no UI framework), `fetch`-based API client (`api/auth.js`), React Context (`AuthContext.jsx`) for global auth/area state.
- **Token storage:** Access and refresh tokens stored in `localStorage`; access token auto-refreshed on expiry using the refresh token. With token rotation now active, each `/refresh` response replaces both the access and refresh tokens in `localStorage`.
- **Two API prefix constants:** `config.js` exports `AUTH_API_PREFIX` (`/api/v1/auth`) and `AREA_API_PREFIX` (`/api/v1/areas`) separately, both pointing at the same `API_BASE_URL`. Auth calls use `AUTH_BASE`; area calls use `AREA_BASE`. Conflating them to a single prefix caused all area requests to 404.
- **Area display (map):** Originally a plain coordinate table fallback due to the network proxy blocking OpenStreetMap tiles. Leaflet was reinstalled (`leaflet`, `react-leaflet`) and `AreaMap.jsx` was recreated using **Esri ArcGIS World_Street_Map tiles** (`server.arcgisonline.com`) which are not blocked by the development proxy. The Esri tile URL scheme uses `{z}/{y}/{x}` (not `{z}/{x}/{y}` as with OpenStreetMap). Leaflet CSS is imported in `main.jsx`.
- **Role-aware UI:**
  - `canManageAreas` gates visibility of the "Create Area" form to Admins only.
  - `isAdmin` prop gates visibility of the "Delete" button on area cards.
  - `RolePill` component visually distinguishes Admin vs Viewer roles.

---

## 8. Infrastructure / Environment Notes

- **Database access:** PostgreSQL was temporarily configured for LAN access (`listen_addresses`, `pg_hba.conf`, Windows Firewall rule) to support testing from a second machine, then reverted to localhost-only afterward.
- **Network restrictions:** The development environment sits behind an authenticating proxy that blocks unauthenticated external HTTPS requests (confirmed via `407 Proxy Authentication Required` on OpenStreetMap tile requests and Google Fonts). Esri ArcGIS tile servers were found to be accessible through the same proxy and are now used for the map component.
- **Virtual environment:** The backend application maintains an isolated `.venv`, created via `python -m venv .venv` and activated before installing dependencies from `requirements.txt`.

---

## 9. Unit Testing

### 9.1 Setup
A `pytest`-based unit test suite lives under `combined-api/tests/`, using `pytest-asyncio` to support the project's fully async codebase. Tests run against a **mocked database session** rather than a real PostgreSQL connection, so the suite runs quickly and without any external dependencies.

**Test files:**
| File | Covers | Database |
|---|---|---|
| `test_security.py` | `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token` | Not needed (pure functions) |
| `test_schemas.py` | Password strength validation, `AreaAssignSchema` polygon validation, `PointCheckSchema` range validation | Not needed (pure functions) |
| `test_audit_logger.py` | `write_audit_log()` | Mocked |
| `test_auth_router.py` | `register()`, `login()` | Mocked |

`conftest.py` provides shared fixtures, including `mock_db` (a fake `AsyncSession`) and `make_scalar_result()`, a helper that simulates what `db.execute(...).scalar_one_or_none()` returns for a given test case, without touching a real database.

### 9.2 Debugging Workflow
- **`print()` statements** are included throughout the test files to surface intermediate values, mocked responses, returned objects, and other variables during execution — useful for inspecting what a function actually returned when a test fails or behaves unexpectedly.
- **All test logic and assertions remain the source of truth** for pass/fail — the print statements are purely diagnostic and do not affect test outcomes.
- **Each test file runs independently**, with no import dependency between test files (shared helper functions are defined locally within each file rather than imported across test modules), so any single file can be executed in isolation.

### 9.3 Running the Tests

Run the full suite:
```powershell
pytest
```

Run an individual file with printed output visible and verbose test names:
```powershell
pytest -s -v tests/test_security.py
pytest -s -v tests/test_schemas.py
pytest -s -v tests/test_audit_logger.py
pytest -s -v tests/test_auth_router.py
```
- `-s` disables pytest's default output capturing, so `print()` statements are visible in the terminal instead of being suppressed.
- `-v` (verbose) lists each individual test by name with its pass/fail result, instead of a compact dot-per-test summary.

### 9.4 Coverage Status
Currently covered: password hashing/token logic, schema validation rules, audit logging, and the `register`/`login` endpoints.

Not yet covered (planned next): `refresh_token()`, `logout()`, `logout_all()`, `unlock_account()`, `update_account_status()` in `routers/auth.py`; all of `routers/areas.py` (`assign_user_area`, `remove_user_area`, `get_user_area`, `check_point`); and `dependencies.py`'s `get_current_user()`/`require_role()`. These follow the same mock-and-assert pattern already established and are considered straightforward extensions of the existing suite.

---

## 10. Summary of Outcomes

- The backend runs as a single, consistent, single-database FastAPI application, avoiding an entire class of bugs related to configuration drift, missing tables, and cross-cutting data inconsistency.
- Role-based access control is enforced **both** in the UI (hiding actions a role shouldn't see) **and** at the API layer (rejecting unauthorized requests regardless of UI state), per standard defense-in-depth practice. A regression that briefly allowed viewers to modify their own area was identified and reverted to the correct admin-only enforcement.
- The redundant Editor role was identified and removed, simplifying the permission model to a clean two-role system: **Admin** (full management) and **Viewer** (read-only, self-scoped).
- Account activation/deactivation was added as an admin capability with **immediate** effect on existing sessions, not just future logins, via a per-request `account_status` check in `get_current_user`.
- Refresh token rotation was implemented — each refresh token is now single-use, with automatic full session revocation on reuse detection.
- Geographic area data is properly modeled with PostGIS, including polygon storage and "is point inside area" checks, backed by an appropriate spatial index.
- Database indexes were reviewed against actual query patterns, redundant indexes removed, and coverage verified via `EXPLAIN ANALYZE`.
- The interactive map component was restored using Esri ArcGIS tiles, which are accessible through the development network's proxy unlike OpenStreetMap.
- A `pytest`-based unit test suite covers core authentication, schema validation, and audit logging logic, with a clear, documented path to extend coverage to the remaining endpoints.

---

## 11. Planned / Recommended Next Steps

- Extend unit test coverage to `areas.py` and the remaining `auth.py` endpoints.
- Add an admin-only "list users" endpoint to support area/status management workflows without direct database access.
- Replace placeholder secrets with securely generated values and move secret management out of checked-in `.env` files for any real deployment.
- Add rate limiting on authentication endpoints.
- Add `ON DELETE CASCADE` to the `user_sessions` foreign key for consistency with `authorized_areas`.
- Add a `README.md` and `.env.example` for project setup and onboarding.

---

