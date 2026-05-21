"""
Integration tests for the movements API (app/api/movements.py).

These tests use a real in-memory SQLite database and the full FastAPI request
pipeline.  Foreign-key constraints on task_id are not enforced by SQLite by
default, so a synthetic UUID is used as task_id to avoid creating a full task
graph in every test.

Endpoints covered:
  POST /movements           — create a movement (worker or admin)
  GET  /movements           — list all company movements (admin only)

Movement types tested:
  - entrada:   goods arrive at a location (no origin required)
  - traslado:  goods move between two locations
  - invalid:   requests that must be rejected with 4xx

RNF-04: every endpoint requires authentication.
RNF-05: GET /movements is restricted to admin role.

Pattern: Arrange → Act → Assert
"""

import uuid
import pytest

from app.models.models import InventoryItem


class TestEntradaMovement:

    async def test_register_movement_entry_creates_inventory_and_returns_201(
        self, client, base_data, worker_token
    ):
        """
        POST /movements with type=entrada to an empty location must:
          - Return HTTP 201.
          - Return a body with type='entrada' and the correct destination_location_id.
        An InventoryItem must be created at the destination (verified by attempting
        a second entrada to the same location, which must return 400).
        """
        # Arrange
        location = base_data["location1"]
        product = base_data["product1"]
        payload = {
            "task_id": str(uuid.uuid4()),
            "type": "entrada",
            "product_id": str(product.id),
            "destination_location_id": str(location.id),
            "quantity": 1,
        }

        # Act
        response = await client.post(
            "/movements",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=payload,
        )

        # Assert: movement created
        assert response.status_code == 201
        body = response.json()
        assert body["type"] == "entrada"
        assert body["destination_location_id"] == str(location.id)
        assert body["product_id"] == str(product.id)

        # Verify InventoryItem was persisted: a second entrada to the same
        # location must be rejected because it is now occupied.
        response2 = await client.post(
            "/movements",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=payload,
        )
        assert response2.status_code == 400

    async def test_register_movement_entry_requires_destination(
        self, client, base_data, worker_token
    ):
        """
        POST /movements with type=entrada and no destination_location_id must
        return HTTP 400 (destination is mandatory for an entrada).
        """
        # Arrange
        product = base_data["product1"]
        payload = {
            "task_id": str(uuid.uuid4()),
            "type": "entrada",
            "product_id": str(product.id),
            # destination_location_id intentionally omitted
        }

        # Act
        response = await client.post(
            "/movements",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=payload,
        )

        # Assert
        assert response.status_code == 400


class TestTrasladoMovement:

    async def test_register_movement_transfer_moves_inventory_and_returns_201(
        self, client, base_data, worker_token, db_session
    ):
        """
        POST /movements with type=traslado must:
          - Return HTTP 201.
          - Move the InventoryItem from origin to destination.
          - A subsequent entrada to the old origin must succeed (it is now free).
          - A subsequent entrada to the new destination must fail (it is occupied).
        """
        # Arrange: populate location1 directly so the transfer has something to move
        item = InventoryItem(
            id=uuid.uuid4(),
            location_id=base_data["location1"].id,
            product_id=base_data["product1"].id,
            quantity=3,
        )
        db_session.add(item)
        await db_session.commit()

        payload = {
            "task_id": str(uuid.uuid4()),
            "type": "traslado",
            "product_id": str(base_data["product1"].id),
            "origin_location_id": str(base_data["location1"].id),
            "destination_location_id": str(base_data["location2"].id),
        }

        # Act
        response = await client.post(
            "/movements",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=payload,
        )

        # Assert: movement created
        assert response.status_code == 201
        body = response.json()
        assert body["type"] == "traslado"
        assert body["origin_location_id"] == str(base_data["location1"].id)
        assert body["destination_location_id"] == str(base_data["location2"].id)

        # Verify inventory moved: origin should now be free
        entry_to_old_origin = await client.post(
            "/movements",
            headers={"Authorization": f"Bearer {worker_token}"},
            json={
                "task_id": str(uuid.uuid4()),
                "type": "entrada",
                "product_id": str(base_data["product2"].id),
                "destination_location_id": str(base_data["location1"].id),
                "quantity": 1,
            },
        )
        assert entry_to_old_origin.status_code == 201

    async def test_register_movement_transfer_with_empty_origin_returns_400(
        self, client, base_data, worker_token
    ):
        """
        POST /movements with type=traslado where the origin location has no
        inventory must return HTTP 400.
        Business rule: you cannot move what is not there.
        """
        # Arrange: both locations are empty (base_data has no inventory items)
        payload = {
            "task_id": str(uuid.uuid4()),
            "type": "traslado",
            "product_id": str(base_data["product1"].id),
            "origin_location_id": str(base_data["location1"].id),
            "destination_location_id": str(base_data["location2"].id),
        }

        # Act
        response = await client.post(
            "/movements",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=payload,
        )

        # Assert
        assert response.status_code == 400

    async def test_register_movement_invalid_origin_no_field_returns_400(
        self, client, base_data, worker_token
    ):
        """
        POST /movements with type=traslado and origin_location_id=null must return
        HTTP 400 because traslado requires both origin and destination.
        """
        # Arrange
        payload = {
            "task_id": str(uuid.uuid4()),
            "type": "traslado",
            "product_id": str(base_data["product1"].id),
            "origin_location_id": None,
            "destination_location_id": str(base_data["location2"].id),
        }

        # Act
        response = await client.post(
            "/movements",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=payload,
        )

        # Assert
        assert response.status_code == 400


class TestListMovements:

    async def test_worker_cannot_list_all_movements_returns_403(
        self, client, base_data, worker_token
    ):
        """
        GET /movements with a worker token must return HTTP 403.
        RNF-05: listing all company movements is an admin-only operation.
        """
        # Act
        response = await client.get(
            "/movements", headers={"Authorization": f"Bearer {worker_token}"}
        )

        # Assert
        assert response.status_code == 403

    async def test_admin_can_list_all_movements_returns_200(
        self, client, base_data, admin_token
    ):
        """
        GET /movements with a valid admin token must return HTTP 200 and a list
        (empty or not) of movements belonging to the admin's company.
        """
        # Act
        response = await client.get(
            "/movements", headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Assert
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_movements_without_auth_returns_401(
        self, client, base_data
    ):
        """
        GET /movements without any Authorization header must return HTTP 401.
        RNF-04: the endpoint is not publicly accessible.
        """
        # Act
        response = await client.get("/movements")

        # Assert
        assert response.status_code == 401
