"""
Coverage-completion tests for the remaining API endpoints.

This file covers endpoints that were not yet exercised:
  POST /auth/register            — new company creation and add-user-to-company flows
  GET  /auth/users               — list company users (admin)
  DELETE /auth/users/{id}        — deactivate a user (admin)
  POST /auth/change-password     — password change flow
  GET/POST/PUT  /boxes           — box management
  GET           /warehouses/{id}/shelves, /shelves/{id}, /shelves/{id}/levels, /levels/{id}
  GET/PUT       /levels/{id}/locations, /locations/{id}, /locations/nfc/{tag}

Pattern: Arrange → Act → Assert
"""

import uuid
import pytest


# ---------------------------------------------------------------------------
# Auth: registration and user management
# ---------------------------------------------------------------------------

class TestAuthRegister:

    async def test_register_new_company_with_admin_returns_201(
        self, client, base_data
    ):
        """
        POST /auth/register with company_name creates a new Company and an admin
        User without requiring authentication.  Returns 201 with the user profile.
        """
        # Act
        response = await client.post(
            "/auth/register",
            json={
                "name": "Brand New Admin",
                "email": "brandnew@other.com",
                "company_name": "Other Company",
                "password": "secret123",
                "role": "admin",
            },
        )

        # Assert
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "brandnew@other.com"
        assert body["role"] == "admin"

    async def test_register_new_company_requires_password_returns_422(
        self, client, base_data
    ):
        """POST /auth/register with company_name but no password must return 422."""
        response = await client.post(
            "/auth/register",
            json={
                "name": "No Password Admin",
                "email": "nopwd@other.com",
                "company_name": "Fails Company",
                "role": "admin",
                # password intentionally omitted
            },
        )
        assert response.status_code == 422

    async def test_register_duplicate_email_returns_400(
        self, client, base_data
    ):
        """POST /auth/register with an e-mail already in use must return 400."""
        response = await client.post(
            "/auth/register",
            json={
                "name": "Dup",
                "email": "admin@test.com",  # already exists in base_data
                "company_name": "Dup Company",
                "password": "secret123",
                "role": "admin",
            },
        )
        assert response.status_code == 400

    async def test_register_add_worker_to_existing_company_returns_201(
        self, client, base_data, admin_token
    ):
        """
        POST /auth/register without company_name, with admin auth, adds a worker to
        the existing company and returns a temporary password.
        """
        # Act
        response = await client.post(
            "/auth/register",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Extra Worker",
                "email": "extra.worker@test.com",
                "role": "worker",
            },
        )

        # Assert
        assert response.status_code == 201
        body = response.json()
        assert body["role"] == "worker"
        assert body["temporary_password"] is not None

    async def test_register_without_company_name_and_no_auth_returns_401(
        self, client, base_data
    ):
        """
        POST /auth/register without company_name and no auth header must return 401.
        There is no way to add a user to a company without admin credentials.
        """
        response = await client.post(
            "/auth/register",
            json={
                "name": "Ghost",
                "email": "ghost@test.com",
                "role": "worker",
            },
        )
        assert response.status_code == 401


class TestAuthUserManagement:

    async def test_admin_can_list_users_returns_200(
        self, client, base_data, admin_token
    ):
        """GET /auth/users must return all active users in the company."""
        response = await client.get(
            "/auth/users", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        emails = [u["email"] for u in response.json()]
        assert "admin@test.com" in emails
        assert "worker@test.com" in emails

    async def test_admin_can_deactivate_user_returns_204(
        self, client, base_data, admin_token
    ):
        """DELETE /auth/users/{id} must deactivate the user (not delete) and return 204."""
        worker_id = str(base_data["worker"].id)
        response = await client.delete(
            f"/auth/users/{worker_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

        # Deactivated user must not appear in the active list
        users_response = await client.get(
            "/auth/users", headers={"Authorization": f"Bearer {admin_token}"}
        )
        active_emails = [u["email"] for u in users_response.json()]
        assert "worker@test.com" not in active_emails

    async def test_admin_cannot_deactivate_self_returns_400(
        self, client, base_data, admin_token
    ):
        """DELETE /auth/users/{id} where id is the calling admin must return 400."""
        admin_id = str(base_data["admin"].id)
        response = await client.delete(
            f"/auth/users/{admin_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400

    async def test_admin_deactivate_unknown_user_returns_404(
        self, client, base_data, admin_token
    ):
        """DELETE /auth/users/{id} for a non-existent user must return 404."""
        response = await client.delete(
            f"/auth/users/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


class TestAuthChangePassword:

    async def test_change_password_with_correct_current_returns_200_and_token(
        self, client, base_data, admin_token
    ):
        """POST /auth/change-password with correct current_password must return a new token."""
        response = await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"current_password": "admin123", "new_password": "newpassword123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body

    async def test_change_password_with_wrong_current_returns_400(
        self, client, base_data, admin_token
    ):
        """POST /auth/change-password with wrong current_password must return 400."""
        response = await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"current_password": "WRONG", "new_password": "newpassword123"},
        )
        assert response.status_code == 400

    async def test_change_password_too_short_returns_422(
        self, client, base_data, admin_token
    ):
        """POST /auth/change-password with a new_password shorter than 8 chars must return 422."""
        response = await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"current_password": "admin123", "new_password": "short"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Boxes CRUD
# ---------------------------------------------------------------------------

class TestBoxesCrud:

    async def test_admin_can_list_boxes_returns_200(
        self, client, base_data, admin_token
    ):
        """GET /boxes must return all boxes for the company including the one in base_data."""
        response = await client.get(
            "/boxes", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 1

    async def test_admin_can_create_box_returns_201(
        self, client, base_data, admin_token
    ):
        """POST /boxes must create a new box linked to a product and return 201."""
        response = await client.post(
            "/boxes",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "product_id": str(base_data["product1"].id),
                "current_quantity": 5,
                "max_capacity": 10,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["current_quantity"] == 5
        assert body["max_capacity"] == 10

    async def test_can_get_box_by_id_returns_200(
        self, client, base_data, worker_token
    ):
        """GET /boxes/{id} must return the box details."""
        box_id = str(base_data["box"].id)
        response = await client.get(
            f"/boxes/{box_id}", headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        assert response.json()["id"] == box_id

    async def test_get_box_not_found_returns_404(
        self, client, base_data, worker_token
    ):
        """GET /boxes/{id} for an unknown box must return 404."""
        response = await client.get(
            f"/boxes/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {worker_token}"},
        )
        assert response.status_code == 404

    async def test_admin_can_update_box_returns_200(
        self, client, base_data, admin_token
    ):
        """PUT /boxes/{id} must update box quantities and return the updated record."""
        box_id = str(base_data["box"].id)
        response = await client.put(
            f"/boxes/{box_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "product_id": str(base_data["product1"].id),
                "current_quantity": 8,
                "max_capacity": 20,
            },
        )
        assert response.status_code == 200
        assert response.json()["current_quantity"] == 8

    async def test_update_nonexistent_box_returns_404(
        self, client, base_data, admin_token
    ):
        """PUT /boxes/{id} for an unknown box must return 404."""
        response = await client.put(
            f"/boxes/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "product_id": str(base_data["product1"].id),
                "current_quantity": 1,
                "max_capacity": 5,
            },
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Shelves and Levels
# ---------------------------------------------------------------------------

class TestShelvesAndLevels:

    async def test_admin_can_list_shelves_for_warehouse(
        self, client, base_data, admin_token
    ):
        """GET /warehouses/{id}/shelves must return the shelves belonging to the warehouse."""
        wid = str(base_data["warehouse"].id)
        response = await client.get(
            f"/warehouses/{wid}/shelves",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) >= 1
        assert body[0]["warehouse_id"] == wid

    async def test_list_shelves_for_unknown_warehouse_returns_404(
        self, client, base_data, admin_token
    ):
        """GET /warehouses/{id}/shelves for a non-existent warehouse must return 404."""
        response = await client.get(
            f"/warehouses/{uuid.uuid4()}/shelves",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_admin_can_get_shelf_by_id_returns_200(
        self, client, base_data, admin_token
    ):
        """GET /shelves/{id} must return the shelf details."""
        sid = str(base_data["shelf"].id)
        response = await client.get(
            f"/shelves/{sid}", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["id"] == sid

    async def test_get_shelf_not_found_returns_404(
        self, client, base_data, admin_token
    ):
        """GET /shelves/{id} for an unknown shelf must return 404."""
        response = await client.get(
            f"/shelves/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_admin_can_list_levels_for_shelf_returns_200(
        self, client, base_data, admin_token
    ):
        """GET /shelves/{id}/levels must return the levels belonging to the shelf."""
        sid = str(base_data["shelf"].id)
        response = await client.get(
            f"/shelves/{sid}/levels",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    async def test_admin_can_get_level_by_id_returns_200(
        self, client, base_data, admin_token
    ):
        """GET /levels/{id} must return the level details."""
        lid = str(base_data["level"].id)
        response = await client.get(
            f"/levels/{lid}", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["id"] == lid

    async def test_get_level_not_found_returns_404(
        self, client, base_data, admin_token
    ):
        """GET /levels/{id} for an unknown level must return 404."""
        response = await client.get(
            f"/levels/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

class TestLocations:

    async def test_can_list_locations_for_level_returns_200(
        self, client, base_data, worker_token
    ):
        """GET /levels/{id}/locations must return all locations under that level."""
        lid = str(base_data["level"].id)
        response = await client.get(
            f"/levels/{lid}/locations",
            headers={"Authorization": f"Bearer {worker_token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 2  # base_data has 2 locations in this level

    async def test_can_get_location_by_id_returns_200(
        self, client, base_data, worker_token
    ):
        """GET /locations/{id} must return the location with its position number."""
        loc_id = str(base_data["location1"].id)
        response = await client.get(
            f"/locations/{loc_id}",
            headers={"Authorization": f"Bearer {worker_token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == loc_id

    async def test_get_location_not_found_returns_404(
        self, client, base_data, worker_token
    ):
        """GET /locations/{id} for a non-existent location must return 404."""
        response = await client.get(
            f"/locations/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {worker_token}"},
        )
        assert response.status_code == 404

    async def test_get_location_by_nfc_not_found_returns_404(
        self, client, base_data, worker_token
    ):
        """GET /locations/nfc/{tag} for an unknown NFC tag must return 404."""
        response = await client.get(
            "/locations/nfc/UNKNOWN_TAG",
            headers={"Authorization": f"Bearer {worker_token}"},
        )
        assert response.status_code == 404

    async def test_admin_can_update_location_nfc_tag_returns_200(
        self, client, base_data, admin_token
    ):
        """PUT /locations/{id}/nfc must assign an NFC tag to a location and return 200."""
        loc_id = str(base_data["location1"].id)
        response = await client.put(
            f"/locations/{loc_id}/nfc",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"nfc_tag": "NFC-TAG-001"},
        )
        assert response.status_code == 200
        assert response.json()["nfc_tag"] == "NFC-TAG-001"

    async def test_update_location_nfc_duplicate_tag_returns_409(
        self, client, base_data, admin_token
    ):
        """
        PUT /locations/{id}/nfc with a tag already used by another location must return 409.
        NFC tags must be globally unique (UNIQUE constraint on Location.nfc_tag).
        """
        # Assign the tag to location1 first
        loc1_id = str(base_data["location1"].id)
        await client.put(
            f"/locations/{loc1_id}/nfc",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"nfc_tag": "NFC-SHARED"},
        )

        # Try to assign the same tag to location2
        loc2_id = str(base_data["location2"].id)
        response = await client.put(
            f"/locations/{loc2_id}/nfc",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"nfc_tag": "NFC-SHARED"},
        )
        assert response.status_code == 409
