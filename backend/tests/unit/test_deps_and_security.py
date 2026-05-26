"""
Unit tests for the auth dependencies (app/api/deps.py) and the security
helpers (app/core/security.py).

These modules are mostly covered indirectly through the auth integration
tests, but a couple of branches were never reached:
  - decode_access_token with an invalid signature → None
  - get_current_user with a token whose `sub` doesn't exist in the DB
  - get_user_from_token rejecting a non-admin user with 403
  - get_current_admin rejecting a worker with 403

Pattern: Arrange → Act → Assert
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user, get_current_admin, get_user_from_token
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.models import User, UserRole


def _mock_db_returning(item):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    db.execute.return_value = result
    return db


# ---------------------------------------------------------------------------
# security.py
# ---------------------------------------------------------------------------

class TestPasswordHashing:

    def test_verify_password_matches_hash(self):
        h = get_password_hash("hunter2")
        assert verify_password("hunter2", h) is True

    def test_verify_password_rejects_wrong_value(self):
        h = get_password_hash("hunter2")
        assert verify_password("wrong", h) is False


class TestJwtTokens:

    def test_encode_and_decode_roundtrip(self):
        token = create_access_token({"sub": "abc", "role": "admin"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "abc"
        assert payload["role"] == "admin"
        assert "exp" in payload  # default expiry attached

    def test_create_access_token_honours_expires_delta(self):
        from datetime import timedelta
        token = create_access_token({"sub": "abc"}, expires_delta=timedelta(seconds=1))
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "abc"

    def test_decode_invalid_token_returns_none(self):
        """A tampered or unparseable token must decode to None, not raise."""
        assert decode_access_token("not.a.jwt") is None
        assert decode_access_token("") is None


# ---------------------------------------------------------------------------
# deps.py
# ---------------------------------------------------------------------------

class TestGetCurrentUser:

    async def test_valid_token_returns_user(self):
        user = MagicMock(spec=User)
        user.id = uuid.uuid4()
        token = create_access_token({"sub": str(user.id)})
        db = _mock_db_returning(user)

        result = await get_current_user(token=token, db=db)

        assert result is user

    async def test_invalid_token_raises_401(self):
        db = _mock_db_returning(None)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="bad-token", db=db)
        assert exc_info.value.status_code == 401

    async def test_token_without_sub_raises_401(self):
        token = create_access_token({"role": "admin"})  # no sub
        db = _mock_db_returning(None)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=db)
        assert exc_info.value.status_code == 401

    async def test_unknown_user_id_raises_401(self):
        token = create_access_token({"sub": str(uuid.uuid4())})
        db = _mock_db_returning(None)  # no user in DB
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=db)
        assert exc_info.value.status_code == 401


class TestGetCurrentAdmin:

    async def test_admin_user_passes_through(self):
        user = MagicMock(spec=User)
        user.role = UserRole.admin
        result = await get_current_admin(current_user=user)
        assert result is user

    async def test_worker_user_raises_403(self):
        user = MagicMock(spec=User)
        user.role = UserRole.worker
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin(current_user=user)
        assert exc_info.value.status_code == 403


class TestGetUserFromToken:
    """Used by /auth/register when adding a worker to a company."""

    async def test_valid_admin_token_returns_user(self):
        admin = MagicMock(spec=User)
        admin.id = uuid.uuid4()
        admin.role = UserRole.admin
        token = create_access_token({"sub": str(admin.id)})
        db = _mock_db_returning(admin)

        result = await get_user_from_token(token, db)
        assert result is admin

    async def test_worker_token_raises_403(self):
        worker = MagicMock(spec=User)
        worker.id = uuid.uuid4()
        worker.role = UserRole.worker
        token = create_access_token({"sub": str(worker.id)})
        db = _mock_db_returning(worker)

        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_token(token, db)
        assert exc_info.value.status_code == 403

    async def test_invalid_token_raises_401(self):
        db = _mock_db_returning(None)
        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_token("garbage", db)
        assert exc_info.value.status_code == 401

    async def test_token_without_sub_raises_401(self):
        token = create_access_token({"role": "admin"})
        db = _mock_db_returning(None)
        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_token(token, db)
        assert exc_info.value.status_code == 401

    async def test_unknown_user_id_raises_401(self):
        token = create_access_token({"sub": str(uuid.uuid4())})
        db = _mock_db_returning(None)
        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_token(token, db)
        assert exc_info.value.status_code == 401
