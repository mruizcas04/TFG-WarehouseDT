"""
Integration tests for authentication endpoints.

Endpoints covered:
  POST /auth/login           — obtain a JWT token
  GET  /auth/me              — read the authenticated user's profile

Tests use a real in-memory SQLite DB (via the shared fixtures in conftest.py)
so that password hashing, JWT generation and DB lookups all go through the
production code paths without mocking.

RNF-04 validation: every protected endpoint must return 401 when no token is provided.

Pattern: Arrange → Act → Assert
"""

import pytest


class TestLogin:

    async def test_login_with_valid_credentials_returns_200_and_token(
        self, client, base_data
    ):
        """
        POST /auth/login with correct username+password must return HTTP 200
        and a JSON body with 'access_token' and token_type='bearer'.
        This is the happy path for authentication.
        """
        # Arrange: admin credentials from base_data
        payload = {"username": "admin@test.com", "password": "admin123"}

        # Act
        response = await client.post("/auth/login", data=payload)

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        # Token must be non-empty
        assert len(body["access_token"]) > 20

    async def test_login_with_wrong_password_returns_401(self, client, base_data):
        """
        POST /auth/login with a wrong password must return HTTP 401.
        The WWW-Authenticate header must be present as per OAuth2 spec.
        """
        # Arrange
        payload = {"username": "admin@test.com", "password": "WRONG_PASSWORD"}

        # Act
        response = await client.post("/auth/login", data=payload)

        # Assert
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    async def test_login_with_unknown_email_returns_401(self, client, base_data):
        """
        POST /auth/login with a non-existent email must return HTTP 401
        (same response as wrong password — intentional, to avoid user enumeration).
        """
        # Arrange
        payload = {"username": "nobody@test.com", "password": "whatever"}

        # Act
        response = await client.post("/auth/login", data=payload)

        # Assert
        assert response.status_code == 401

    async def test_login_for_inactive_user_returns_401(self, client, base_data, db_session):
        """
        POST /auth/login for a deactivated account must return HTTP 401.
        Inactive users must not be able to obtain tokens even with the right password.
        """
        # Arrange: deactivate the worker
        worker = base_data["worker"]
        worker.is_active = False
        db_session.add(worker)
        await db_session.commit()

        payload = {"username": "worker@test.com", "password": "worker123"}

        # Act
        response = await client.post("/auth/login", data=payload)

        # Assert
        assert response.status_code == 401


class TestProtectedEndpoints:

    async def test_protected_endpoint_without_token_returns_401(
        self, client, base_data
    ):
        """
        GET /auth/me without an Authorization header must return HTTP 401.
        RNF-04: authentication is required on all endpoints except /auth/login.
        """
        # Act — no header
        response = await client.get("/auth/me")

        # Assert
        assert response.status_code == 401

    async def test_protected_endpoint_with_invalid_token_returns_401(
        self, client, base_data
    ):
        """
        GET /auth/me with a syntactically invalid JWT must return HTTP 401.
        """
        # Act
        response = await client.get(
            "/auth/me", headers={"Authorization": "Bearer not.a.real.token"}
        )

        # Assert
        assert response.status_code == 401

    async def test_protected_endpoint_with_valid_admin_token_returns_200(
        self, client, base_data, admin_token
    ):
        """
        GET /auth/me with a valid admin JWT must return HTTP 200 and the admin's
        profile, including role=admin.
        """
        # Act
        response = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "admin@test.com"
        assert body["role"] == "admin"

    async def test_protected_endpoint_with_valid_worker_token_returns_200(
        self, client, base_data, worker_token
    ):
        """
        GET /auth/me with a valid worker JWT must return HTTP 200 and the worker's
        profile, confirming that non-admin tokens are accepted on public-to-authenticated
        endpoints.
        """
        # Act
        response = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {worker_token}"}
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "worker@test.com"
        assert body["role"] == "worker"
