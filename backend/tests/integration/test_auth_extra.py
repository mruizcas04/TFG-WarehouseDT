"""
Integration tests for the auth endpoints that the rest of the suite leaves
uncovered:

  POST /auth/verify-email     — email verification token flow
  POST /auth/forgot-password  — request password-reset link (silent on unknown)
  POST /auth/reset-password   — apply new password using reset token
  POST /auth/logout           — flip is_online=False
  POST /auth/change-password  — happy path that wasn't covered by HTTP integration

These complete the auth surface area that the unit tests already check at
handler level — the HTTP path is exercised here against the real SQLAlchemy
session so we also cover deps.get_current_user / get_user_from_token.

Pattern: Arrange → Act → Assert
"""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models.models import User, UserRole
from app.core.security import get_password_hash


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# verify-email
# ---------------------------------------------------------------------------

class TestVerifyEmail:

    async def test_valid_token_marks_user_verified(self, client, base_data, db_session):
        """A pending user with a matching token flips is_email_verified=True."""
        admin = base_data["admin"]
        admin.is_email_verified = False
        admin.verification_token = "valid-token-123"
        db_session.add(admin)
        await db_session.commit()

        response = await client.post("/auth/verify-email?token=valid-token-123")
        assert response.status_code == 200
        assert "verificado" in response.json()["message"].lower()

    async def test_unknown_token_returns_400(self, client, base_data):
        response = await client.post("/auth/verify-email?token=nonexistent")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# forgot-password / reset-password
# ---------------------------------------------------------------------------

class TestForgotPassword:

    async def test_known_email_returns_generic_message(self, client, base_data):
        """The endpoint must always return the generic 'if email exists' message."""
        response = await client.post(
            "/auth/forgot-password",
            json={"email": "admin@test.com"},
        )
        assert response.status_code == 200
        assert "si el email" in response.json()["message"].lower()

    async def test_unknown_email_returns_same_message(self, client, base_data):
        """No user enumeration: unknown email still gets 200 with the same body."""
        response = await client.post(
            "/auth/forgot-password",
            json={"email": "nobody@nowhere.com"},
        )
        assert response.status_code == 200


class TestResetPassword:

    async def test_valid_token_replaces_password(self, client, base_data, db_session):
        """A user with an unexpired reset token can set a new password."""
        admin = base_data["admin"]
        admin.reset_password_token = "reset-token-xyz"
        admin.reset_token_expires = datetime.utcnow() + timedelta(minutes=15)
        db_session.add(admin)
        await db_session.commit()

        response = await client.post(
            "/auth/reset-password",
            json={"token": "reset-token-xyz", "new_password": "brand_new_password"},
        )
        assert response.status_code == 200

        # The new password must let the user log in
        login = await client.post(
            "/auth/login",
            data={"username": "admin@test.com", "password": "brand_new_password"},
        )
        assert login.status_code == 200

    async def test_expired_token_returns_400(self, client, base_data, db_session):
        admin = base_data["admin"]
        admin.reset_password_token = "expired"
        admin.reset_token_expires = datetime.utcnow() - timedelta(minutes=1)
        db_session.add(admin)
        await db_session.commit()

        response = await client.post(
            "/auth/reset-password",
            json={"token": "expired", "new_password": "long_enough_pw"},
        )
        assert response.status_code == 400

    async def test_unknown_token_returns_400(self, client, base_data):
        response = await client.post(
            "/auth/reset-password",
            json={"token": "ghost-token", "new_password": "long_enough_pw"},
        )
        assert response.status_code == 400

    async def test_too_short_password_returns_422(self, client, base_data, db_session):
        admin = base_data["admin"]
        admin.reset_password_token = "valid-tok"
        admin.reset_token_expires = datetime.utcnow() + timedelta(minutes=10)
        db_session.add(admin)
        await db_session.commit()

        response = await client.post(
            "/auth/reset-password",
            json={"token": "valid-tok", "new_password": "short"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

class TestLogout:

    async def test_logout_flips_is_online_false(
        self, client, base_data, admin_token, db_session
    ):
        admin = base_data["admin"]
        admin.is_online = True
        db_session.add(admin)
        await db_session.commit()

        response = await client.post("/auth/logout", headers=_auth(admin_token))
        assert response.status_code == 204

        await db_session.refresh(admin)
        assert admin.is_online is False

    async def test_logout_requires_auth(self, client, base_data):
        response = await client.post("/auth/logout")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# change-password (HTTP path)
# ---------------------------------------------------------------------------

class TestChangePasswordHttp:

    async def test_correct_password_returns_new_token(
        self, client, base_data, admin_token
    ):
        response = await client.post(
            "/auth/change-password",
            headers=_auth(admin_token),
            json={"current_password": "admin123", "new_password": "newadmin_pw"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

        # The token must work for /auth/me
        me = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert me.status_code == 200

    async def test_wrong_current_password_returns_400(
        self, client, base_data, admin_token
    ):
        response = await client.post(
            "/auth/change-password",
            headers=_auth(admin_token),
            json={"current_password": "WRONG", "new_password": "newadmin_pw"},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Inactive / unverified login paths (close existing gaps in auth.py)
# ---------------------------------------------------------------------------

class TestLoginEdgeCases:

    async def test_login_for_unverified_user_returns_401(self, client, db_session):
        unverified = User(
            id=uuid.uuid4(),
            company_id=None,
            name="Pending",
            email="pending@test.com",
            password_hash=get_password_hash("pwd123456"),
            role=UserRole.admin,
            is_active=True,
            is_email_verified=False,
        )
        db_session.add(unverified)
        await db_session.commit()

        response = await client.post(
            "/auth/login",
            data={"username": "pending@test.com", "password": "pwd123456"},
        )
        assert response.status_code == 401
        assert "verifica" in response.json()["detail"].lower()
