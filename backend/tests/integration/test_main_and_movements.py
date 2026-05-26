"""
Integration tests covering surfaces left out of the rest of the suite:

  GET  /health          — liveness probe (app/main.py)
  WS   /ws              — JWT-gated WebSocket endpoint (app/main.py)
  POST /movements       — traslado happy/error paths and box-based salida
                          branches in app/api/movements.py

The WebSocket tests use FastAPI's TestClient (sync) because httpx's
AsyncClient does not speak the WebSocket protocol; this is the standard
pattern documented by FastAPI itself.

Pattern: Arrange → Act → Assert
"""

import uuid
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.models import (
    Box, InventoryItem, MovementType, Task, TaskType,
)
from app.core.security import create_access_token


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:

    async def test_health_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /ws — WebSocket endpoint
# ---------------------------------------------------------------------------

class TestWebSocket:
    """
    Sync TestClient required: httpx.AsyncClient cannot upgrade to a WebSocket.
    Uses the app directly (no DB needed because /ws only checks the JWT).
    """

    def test_invalid_token_closes_immediately(self):
        with TestClient(app) as tc:
            from starlette.websockets import WebSocketDisconnect
            with pytest.raises(WebSocketDisconnect) as exc:
                with tc.websocket_connect("/ws?token=invalid"):
                    pass
            assert exc.value.code == 1008

    def test_valid_token_accepts_connection(self):
        token = create_access_token({"sub": str(uuid.uuid4())})
        with TestClient(app) as tc:
            with tc.websocket_connect(f"/ws?token={token}") as ws:
                # If we got here, the server accepted the upgrade.
                # Close the connection from our side to end the handler loop.
                ws.close()


# ---------------------------------------------------------------------------
# /movements — branches not covered by the existing service tests
# ---------------------------------------------------------------------------

class TestMovementsHttp:

    async def _seed_task(self, db_session, base_data, **overrides):
        admin = base_data["admin"]
        worker = base_data["worker"]
        task = Task(
            id=uuid.uuid4(),
            company_id=admin.company_id,
            created_by=admin.id,
            assigned_to=worker.id,
            type=overrides.get("type", TaskType.entrada),
            destination_location_id=overrides.get("destination_location_id"),
            origin_location_id=overrides.get("origin_location_id"),
        )
        db_session.add(task)
        await db_session.commit()
        return task

    async def test_list_movements_empty(self, client, base_data, admin_token):
        response = await client.get("/movements", headers=_auth(admin_token))
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_entrada_with_quantity_one_loose_product(
        self, client, base_data, admin_token, db_session
    ):
        """quantity=1 entrada stores the product directly without creating a Box."""
        admin = base_data["admin"]
        loc = base_data["location1"]
        product = base_data["product1"]
        task = await self._seed_task(
            db_session, base_data, destination_location_id=loc.id
        )

        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            response = await client.post(
                "/movements",
                headers=_auth(admin_token),
                json={
                    "task_id": str(task.id),
                    "type": "entrada",
                    "product_id": str(product.id),
                    "destination_location_id": str(loc.id),
                    "quantity": 1,
                },
            )

        assert response.status_code == 201
        # InventoryItem points to product directly, no box
        from sqlalchemy import select
        item = (await db_session.execute(
            select(InventoryItem).where(InventoryItem.location_id == loc.id)
        )).scalar_one()
        assert item.product_id == product.id
        assert item.box_id is None

    async def test_create_entrada_with_quantity_greater_than_one_creates_box(
        self, client, base_data, admin_token, db_session
    ):
        """quantity>1 entrada auto-creates a Box."""
        loc = base_data["location1"]
        product = base_data["product1"]
        task = await self._seed_task(
            db_session, base_data, destination_location_id=loc.id
        )

        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            response = await client.post(
                "/movements",
                headers=_auth(admin_token),
                json={
                    "task_id": str(task.id),
                    "type": "entrada",
                    "product_id": str(product.id),
                    "destination_location_id": str(loc.id),
                    "quantity": 3,
                },
            )

        assert response.status_code == 201
        from sqlalchemy import select
        item = (await db_session.execute(
            select(InventoryItem).where(InventoryItem.location_id == loc.id)
        )).scalar_one()
        assert item.box_id is not None
        box = (await db_session.execute(select(Box).where(Box.id == item.box_id))).scalar_one()
        assert box.current_quantity == 3
        assert box.max_capacity == 3

    async def test_create_entrada_without_destination_returns_400(
        self, client, base_data, admin_token, db_session
    ):
        product = base_data["product1"]
        task = await self._seed_task(
            db_session, base_data, destination_location_id=base_data["location1"].id
        )
        response = await client.post(
            "/movements",
            headers=_auth(admin_token),
            json={
                "task_id": str(task.id),
                "type": "entrada",
                "product_id": str(product.id),
            },
        )
        assert response.status_code == 400

    async def test_create_movement_without_product_or_box_returns_400(
        self, client, base_data, admin_token, db_session
    ):
        task = await self._seed_task(
            db_session, base_data, destination_location_id=base_data["location1"].id
        )
        response = await client.post(
            "/movements",
            headers=_auth(admin_token),
            json={
                "task_id": str(task.id),
                "type": "entrada",
                "destination_location_id": str(base_data["location1"].id),
            },
        )
        assert response.status_code == 400

    async def test_create_salida_without_origin_returns_400(
        self, client, base_data, admin_token, db_session
    ):
        product = base_data["product1"]
        task = await self._seed_task(
            db_session, base_data, type=TaskType.salida,
            origin_location_id=base_data["location1"].id,
        )
        response = await client.post(
            "/movements",
            headers=_auth(admin_token),
            json={
                "task_id": str(task.id),
                "type": "salida",
                "product_id": str(product.id),
            },
        )
        assert response.status_code == 400

    async def test_traslado_succeeds_between_locations(
        self, client, base_data, admin_token, db_session
    ):
        """
        Traslado moves an InventoryItem from origin → destination, leaves origin
        free, marks destination occupied.
        """
        origin = base_data["location1"]
        dest = base_data["location2"]
        product = base_data["product1"]
        task = await self._seed_task(
            db_session, base_data, type=TaskType.traslado,
            origin_location_id=origin.id, destination_location_id=dest.id,
        )
        # Seed origin with a loose product
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=origin.id,
            product_id=product.id,
            quantity=1,
        ))
        await db_session.commit()

        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            response = await client.post(
                "/movements",
                headers=_auth(admin_token),
                json={
                    "task_id": str(task.id),
                    "type": "traslado",
                    "origin_location_id": str(origin.id),
                    "destination_location_id": str(dest.id),
                    "product_id": str(product.id),
                },
            )

        assert response.status_code == 201
        from sqlalchemy import select
        # destination now has the item; origin no longer does
        dest_item = (await db_session.execute(
            select(InventoryItem).where(InventoryItem.location_id == dest.id)
        )).scalar_one_or_none()
        origin_item = (await db_session.execute(
            select(InventoryItem).where(InventoryItem.location_id == origin.id)
        )).scalar_one_or_none()
        assert dest_item is not None
        assert origin_item is None

    async def test_traslado_to_occupied_destination_returns_400(
        self, client, base_data, admin_token, db_session
    ):
        origin = base_data["location1"]
        dest = base_data["location2"]
        product = base_data["product1"]
        task = await self._seed_task(
            db_session, base_data, type=TaskType.traslado,
            origin_location_id=origin.id, destination_location_id=dest.id,
        )
        db_session.add_all([
            InventoryItem(
                id=uuid.uuid4(),
                location_id=origin.id,
                product_id=product.id,
                quantity=1,
            ),
            InventoryItem(
                id=uuid.uuid4(),
                location_id=dest.id,
                product_id=product.id,
                quantity=1,
            ),
        ])
        await db_session.commit()

        response = await client.post(
            "/movements",
            headers=_auth(admin_token),
            json={
                "task_id": str(task.id),
                "type": "traslado",
                "origin_location_id": str(origin.id),
                "destination_location_id": str(dest.id),
                "product_id": str(product.id),
            },
        )
        assert response.status_code == 400

    async def test_traslado_without_inventory_at_origin_returns_400(
        self, client, base_data, admin_token, db_session
    ):
        origin = base_data["location1"]
        dest = base_data["location2"]
        product = base_data["product1"]
        task = await self._seed_task(
            db_session, base_data, type=TaskType.traslado,
            origin_location_id=origin.id, destination_location_id=dest.id,
        )

        response = await client.post(
            "/movements",
            headers=_auth(admin_token),
            json={
                "task_id": str(task.id),
                "type": "traslado",
                "origin_location_id": str(origin.id),
                "destination_location_id": str(dest.id),
                "product_id": str(product.id),
            },
        )
        assert response.status_code == 400

    async def test_get_movement_by_id_and_by_task(
        self, client, base_data, admin_token, db_session
    ):
        """Both /movements/{id} and /movements/task/{id} round-trip the data."""
        from app.models.models import Movement
        admin = base_data["admin"]
        task = await self._seed_task(
            db_session, base_data, destination_location_id=base_data["location1"].id
        )
        mv_id = uuid.uuid4()
        db_session.add(Movement(
            id=mv_id,
            company_id=admin.company_id,
            task_id=task.id,
            performed_by=admin.id,
            type=MovementType.entrada,
            destination_location_id=base_data["location1"].id,
        ))
        await db_session.commit()

        r1 = await client.get(f"/movements/{mv_id}", headers=_auth(admin_token))
        assert r1.status_code == 200
        assert r1.json()["id"] == str(mv_id)

        r2 = await client.get(f"/movements/task/{task.id}", headers=_auth(admin_token))
        assert r2.status_code == 200
        assert len(r2.json()) == 1

    async def test_get_unknown_movement_returns_404(
        self, client, base_data, admin_token
    ):
        response = await client.get(f"/movements/{uuid.uuid4()}", headers=_auth(admin_token))
        assert response.status_code == 404
