# Combined API

A FastAPI backend that provides JWT-based authentication, role-based access control, and PostGIS-powered geospatial area authorization. Users can be assigned a polygon area, and any authenticated user can check whether a GPS coordinate falls within their authorized area.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Environment Setup](#environment-setup)
5. [Database Setup](#database-setup)
6. [Running the Application](#running-the-application)
7. [Running Tests](#running-tests)
8. [API Usage Examples](#api-usage-examples)

---

## Project Overview

| Feature | Detail |
|---|---|
| Framework | FastAPI (async) |
| Database | PostgreSQL + PostGIS (via SQLAlchemy 2 async + asyncpg) |
| Auth | JWT access tokens (15 min) + refresh tokens (7 days) |
| Roles | `admin`, `viewer` |
| Geospatial | GeoAlchemy2 + Shapely — polygon assignment and point-in-polygon checks |
| Audit | Every mutating action writes a row to `audit_logs` |

### Directory structure

```
combined-api/
├── app/
│   ├── main.py              # FastAPI app, CORS, router mounts
│   ├── core/
│   │   ├── config.py        # pydantic-settings (reads .env)
│   │   ├── security.py      # password hashing, JWT creation
│   │   ├── dependencies.py  # get_db, get_current_user, require_role
│   │   ├── audit_logger.py  # write_audit_log helper
│   │   └── audit_actions.py # AuditAction string constants
│   ├── db/session.py        # async engine + sessionmaker
│   ├── models/              # SQLAlchemy ORM models
│   ├── routers/
│   │   ├── auth.py          # /api/v1/auth endpoints
│   │   └── areas.py         # /api/v1/areas endpoints
│   └── schemas/             # Pydantic request/response models
└── tests/
    ├── conftest.py
    ├── test_security.py
    ├── test_schemas.py
    ├── test_audit_logger.py
    ├── test_auth_router.py
    └── test_areas.py
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| PostgreSQL | 14+ with **PostGIS** extension enabled |
| pip | latest |

Install PostGIS on Ubuntu/Debian:
```bash
sudo apt install postgresql-14-postgis-3
```

On macOS with Homebrew:
```bash
brew install postgis
```

---

## Installation

```bash
# 1. Clone the repository and enter the project folder
git clone <repo-url>
cd combined-api

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install runtime dependencies
pip install -r requirements.txt

# 4. Install test dependencies
pip install -r requirements-test.txt
```

---

## Environment Setup

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# PostgreSQL connection — update user, password, host, and database name
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/auth_db

# Two DIFFERENT high-entropy secrets for signing JWTs.
# Generate each with:
#   python -c "import secrets; print(secrets.token_hex(32))"
ACCESS_TOKEN_SECRET=<64-char hex string>
REFRESH_TOKEN_SECRET=<different 64-char hex string>

ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256
```

> **Important:** `ACCESS_TOKEN_SECRET` and `REFRESH_TOKEN_SECRET` **must be different**. Using the same value allows refresh tokens to be accepted as access tokens, which is a security vulnerability.

---

## Database Setup

### 1. Create the database and enable PostGIS

```sql
-- Run in psql as a superuser
CREATE DATABASE auth_db;
\c auth_db
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 2. Create tables

There is no Alembic migration folder yet. Create all tables from the Python shell:

```bash
# From inside combined-api/, with your virtual environment active
python - <<'EOF'
import asyncio
from app.db.session import engine, Base
# Import all models so SQLAlchemy registers them
from app.models import user, session, audit_log, authorized_area  # noqa: F401

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

asyncio.run(create())
EOF
```

---

## Running the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/](http://localhost:8000/)

---

## Running Tests

Tests use `pytest-asyncio` with no real database — all DB calls are mocked.

```bash
# Run all tests with visible print() output
pytest -s -v tests/

# Run a specific test file
pytest -s -v tests/test_security.py
pytest -s -v tests/test_schemas.py
pytest -s -v tests/test_audit_logger.py
pytest -s -v tests/test_auth_router.py
pytest -s -v tests/test_areas.py

# Run a single test class or function
pytest -s -v tests/test_areas.py::TestCheckPoint
pytest -s -v tests/test_areas.py::TestCheckPoint::test_point_inside_area_returns_true
```

---

## API Usage Examples

All examples use `curl`. Replace `<ACCESS_TOKEN>` with the token returned by `/login`.

### Auth endpoints — `/api/v1/auth`

#### Register a new user

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "alice",
    "email": "alice@example.com",
    "phone_no": "9876543210",
    "password": "Secure1!",
    "role": "viewer"
  }'
```

#### Log in

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "Secure1!",
    "platform": "web"
  }'
# Response: { "access_token": "...", "refresh_token": "..." }
```

#### Get current user profile

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

#### Refresh access token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{ "refresh_token": "<REFRESH_TOKEN>" }'
```

#### Logout (invalidate one session)

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{ "refresh_token": "<REFRESH_TOKEN>" }'
```

#### List all users — admin only

```bash
curl http://localhost:8000/api/v1/auth/users \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
# Returns: [{ "user_id": "...", "user_name": "...", "email": "...",
#             "role": "viewer", "account_status": "ACTIVATED", "has_area": false }, ...]
```

Use the `user_id` values from this response when calling area-assignment endpoints.

#### Activate / deactivate a user account — admin only

```bash
curl -X PUT http://localhost:8000/api/v1/auth/users/<USER_ID>/status \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{ "account_status": "DEACTIVATED" }'
```

---

### Area endpoints — `/api/v1/areas`

#### Assign a polygon area to a user — admin only

Coordinates are `[longitude, latitude]` pairs forming a polygon (minimum 3 points).

```bash
curl -X PUT http://localhost:8000/api/v1/areas/users/<USER_ID> \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "coordinates": [
      [72.5, 18.5],
      [73.0, 18.5],
      [73.0, 19.0],
      [72.5, 19.0]
    ]
  }'
```

#### Get a user's assigned area

Admins can query any user. Regular users can only query themselves.

```bash
curl http://localhost:8000/api/v1/areas/users/<USER_ID> \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
# Response: { "user_id": "...", "has_area": true, "area": { "type": "Polygon", ... } }
```

#### Check if a point is inside the caller's area

```bash
curl -X POST http://localhost:8000/api/v1/areas/check-point \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{ "longitude": 72.88, "latitude": 19.08 }'
# Response: { "inside": true }
```

#### Remove a user's area — admin only

```bash
curl -X DELETE http://localhost:8000/api/v1/areas/users/<USER_ID> \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
```

#### View audit logs — admin only

```bash
curl "http://localhost:8000/api/v1/areas/audit?limit=20&offset=0" \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
```
