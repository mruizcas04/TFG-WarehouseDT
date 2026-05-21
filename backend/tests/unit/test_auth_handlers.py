"""
Unit tests for auth handler functions (app/api/auth.py).

Handlers are called directly with mocked DB sessions, form data, and
request objects — no HTTP stack involved.  This ensures that
coverage.py traces the function bodies.

Pattern: Arrange → Act → Assert
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.auth import (
    login,
    register,
    get_me,
    get_users,
    deactivate_user,
    change_password,
)
from app.core.security import get_password_hash
from app.models.models import User, UserRole, Company
from app.schemas.schemas import UserCreate, ChangePasswordRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_user(
    password="correct123",
    is_active=True,
    role=UserRole.admin,
    must_change_password=False,
):
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.company_id = uuid.uuid4()
    user.name = "Test User"
    user.email = "test@example.com"
    user.password_hash = get_password_hash(password)
    user.is_active = is_active
    user.role = role
    user.must_change_password = must_change_password
    return user


def _make_result_single(item):
    r = MagicMock()
    r.scalar_one_or_none.return_value = item
    return r


def _make_result_list(*items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = list(items)
    return r


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

class TestLogin:

    async def test_valid_credentials_return_access_token(self):
        """login returns a token dict when email and password are correct."""
        db = _mock_db()
        user = _make_user(password="admin123")
        db.execute.return_value = _make_result_single(user)

        form_data = MagicMock(username="admin@test.com", password="admin123")
        result = await login(form_data=form_data, db=db)

        assert "access_token" in result
        assert result["token_type"] == "bearer"

    async def test_wrong_password_raises_401(self):
        """login raises HTTP 401 when the password does not match."""
        db = _mock_db()
        user = _make_user(password="correct")
        db.execute.return_value = _make_result_single(user)

        form_data = MagicMock(username="admin@test.com", password="WRONG")

        with pytest.raises(HTTPException) as exc_info:
            await login(form_data=form_data, db=db)

        assert exc_info.value.status_code == 401

    async def test_unknown_user_raises_401(self):
        """login raises HTTP 401 when the email is not in the DB."""
        db = _mock_db()
        db.execute.return_value = _make_result_single(None)

        form_data = MagicMock(username="nobody@test.com", password="whatever")

        with pytest.raises(HTTPException) as exc_info:
            await login(form_data=form_data, db=db)

        assert exc_info.value.status_code == 401

    async def test_inactive_user_raises_401(self):
        """login raises HTTP 401 for a correct password but deactivated account."""
        db = _mock_db()
        user = _make_user(password="pw123", is_active=False)
        db.execute.return_value = _make_result_single(user)

        form_data = MagicMock(username=user.email, password="pw123")

        with pytest.raises(HTTPException) as exc_info:
            await login(form_data=form_data, db=db)

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------

class TestRegister:

    async def test_new_company_creates_admin_and_returns_user(self):
        """
        register with company_name creates a Company and admin User,
        commits them, and returns the new user without a temporary password.
        db.refresh is mocked to set created_at (server-side default that only
        fires during a real INSERT).
        """
        db = _mock_db()
        db.execute.return_value = _make_result_single(None)  # no duplicate email

        async def set_server_defaults(obj):
            obj.created_at = datetime(2024, 1, 1)
            obj.is_active = True

        db.refresh.side_effect = set_server_defaults

        user_data = UserCreate(
            name="New Admin",
            email="newadmin@company.com",
            password="secret123",
            role=UserRole.admin,
            company_name="New Company",
        )
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""

        result = await register(user_data=user_data, request=mock_request, db=db)

        db.commit.assert_awaited_once()
        assert result.temporary_password is None
        assert result.email == "newadmin@company.com"

    async def test_duplicate_email_raises_400(self):
        """register raises HTTP 400 when the email is already in use."""
        db = _mock_db()
        existing_user = _make_user()
        db.execute.return_value = _make_result_single(existing_user)

        user_data = UserCreate(
            name="Dup",
            email="dup@company.com",
            password="secret123",
            role=UserRole.admin,
            company_name="Company",
        )
        mock_request = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await register(user_data=user_data, request=mock_request, db=db)

        assert exc_info.value.status_code == 400

    async def test_new_company_missing_password_raises_422(self):
        """register raises HTTP 422 when company_name is set but no password is provided."""
        db = _mock_db()
        db.execute.return_value = _make_result_single(None)  # no duplicate

        user_data = UserCreate(
            name="No Pwd",
            email="nopwd@company.com",
            role=UserRole.admin,
            company_name="Company",
            # password intentionally omitted
        )
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""

        with pytest.raises(HTTPException) as exc_info:
            await register(user_data=user_data, request=mock_request, db=db)

        assert exc_info.value.status_code == 422

    async def test_add_user_without_auth_raises_401(self):
        """
        register without company_name and without an Authorization header
        raises HTTP 401 (cannot add user to company without admin token).
        """
        db = _mock_db()
        db.execute.return_value = _make_result_single(None)

        user_data = UserCreate(
            name="Worker",
            email="worker@co.com",
            role=UserRole.worker,
            # no company_name, no password
        )
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""  # no Authorization header

        with pytest.raises(HTTPException) as exc_info:
            await register(user_data=user_data, request=mock_request, db=db)

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_me
# ---------------------------------------------------------------------------

class TestGetMe:

    async def test_returns_current_user(self):
        """get_me simply returns the current_user dependency value."""
        current_user = _make_user()

        result = await get_me(current_user=current_user)

        assert result is current_user


# ---------------------------------------------------------------------------
# get_users
# ---------------------------------------------------------------------------

class TestGetUsers:

    async def test_admin_lists_active_users(self):
        """get_users returns the list of active users in the company."""
        db = _mock_db()
        admin = _make_user()
        worker = _make_user(role=UserRole.worker)
        db.execute.return_value = _make_result_list(admin, worker)

        result = await get_users(db=db, current_user=admin, show_inactive=False)

        assert len(result) == 2

    async def test_show_inactive_flag_changes_filter(self):
        """get_users with show_inactive=True fetches inactive users."""
        db = _mock_db()
        admin = _make_user()
        inactive = _make_user(is_active=False)
        db.execute.return_value = _make_result_list(inactive)

        result = await get_users(db=db, current_user=admin, show_inactive=True)

        db.execute.assert_awaited_once()
        assert len(result) == 1


# ---------------------------------------------------------------------------
# deactivate_user
# ---------------------------------------------------------------------------

class TestDeactivateUser:

    async def test_deactivates_found_user(self):
        """deactivate_user sets is_active=False and commits."""
        db = _mock_db()
        admin = _make_user()
        target = _make_user(role=UserRole.worker)
        db.execute.return_value = _make_result_single(target)

        await deactivate_user(user_id=target.id, db=db, current_user=admin)

        assert target.is_active is False
        db.commit.assert_awaited_once()

    async def test_not_found_raises_404(self):
        """deactivate_user raises HTTP 404 when user_id is not in the company."""
        db = _mock_db()
        admin = _make_user()
        db.execute.return_value = _make_result_single(None)

        with pytest.raises(HTTPException) as exc_info:
            await deactivate_user(user_id=uuid.uuid4(), db=db, current_user=admin)

        assert exc_info.value.status_code == 404

    async def test_deactivating_self_raises_400(self):
        """deactivate_user raises HTTP 400 when the admin tries to deactivate themselves."""
        db = _mock_db()
        admin = _make_user()

        with pytest.raises(HTTPException) as exc_info:
            await deactivate_user(user_id=admin.id, db=db, current_user=admin)

        assert exc_info.value.status_code == 400
        db.execute.assert_not_awaited()


# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------

class TestChangePassword:

    async def test_correct_password_updates_hash_and_returns_token(self):
        """change_password updates password_hash, clears must_change_password, returns token."""
        db = _mock_db()
        user = _make_user(password="old_password123")
        user.must_change_password = True

        data = ChangePasswordRequest(
            current_password="old_password123",
            new_password="new_password456",
        )

        result = await change_password(data=data, current_user=user, db=db)

        db.commit.assert_awaited_once()
        assert user.must_change_password is False
        assert "access_token" in result

    async def test_wrong_current_password_raises_400(self):
        """change_password raises HTTP 400 when current_password is incorrect."""
        db = _mock_db()
        user = _make_user(password="correct_password")

        data = ChangePasswordRequest(
            current_password="WRONG_PASSWORD",
            new_password="newpassword123",
        )

        with pytest.raises(HTTPException) as exc_info:
            await change_password(data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 400

    async def test_too_short_new_password_raises_422(self):
        """change_password raises HTTP 422 when new_password is shorter than 8 chars."""
        db = _mock_db()
        user = _make_user(password="current123")

        data = ChangePasswordRequest(
            current_password="current123",
            new_password="short",
        )

        with pytest.raises(HTTPException) as exc_info:
            await change_password(data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 422
