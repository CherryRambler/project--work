"""
Shared pytest fixtures.

Place this whole `tests/` folder inside your `combined-api/` project root,
next to the `app/` folder, so imports like `from app.core.security import ...`
resolve correctly.
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def sample_user_id():
    """A fixed UUID to use across tests, so assertions are predictable."""
    return uuid.uuid4()


@pytest.fixture
def mock_db():
    """
    A fake AsyncSession that behaves like the real one just enough for
    testing your endpoint logic, without touching a real database.

    - db.execute(...) returns a MagicMock you can configure per-test
      (see examples in test_auth_service.py)
    - db.add(...), db.commit(...), db.flush(...), db.refresh(...) are
      no-ops that just record they were called, so you can assert on them
    """
    db = AsyncMock()
    db.add = MagicMock()  # add() is sync in real SQLAlchemy, not async
    return db


def make_scalar_result(return_value):
    """
    Helper: builds a fake object that mimics what
    `await db.execute(select(...))` returns, so that
    `result.scalar_one_or_none()` gives back `return_value`.

    Usage in a test:
        mock_db.execute.return_value = make_scalar_result(None)
        # now `await get_user_by_email(db, "x@x.com")` will return None
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = return_value
    return result