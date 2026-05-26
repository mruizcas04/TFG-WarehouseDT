"""
Integration tests for the accumulation and box-based flows that the existing
suite touches only superficially.

Areas hit:
  * tasks.py – entrada onto an already-occupied location when the product
    allows accumulation (`units_per_location`) and the salida/traslado
    branches that need to inspect the origin's box.
  * movements.py – partial and full salida that mutate or remove a Box.

These flows are the trickiest in the codebase because they interleave
InventoryItem + Box state, so the assertions verify the DB state after
each call rather than just the response shape.

Pattern: Arrange → Act → Assert
"""

import uuid
from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy import select

from app.models.models import (
    Box, InventoryItem, Movement, MovementType, Product,
    Task, TaskStatus, TaskType,
)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _seed_task(db_session, base_data, **overrides):
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
        product_id=overrides.get("product_id"),
        quantity=overrides.get("quantity"),
    )
    db_session.add(task)
    await db_session.commit()
    return task


# ---------------------------------------------------------------------------
# Tasks.entrada — accumulation onto an occupied location
# ---------------------------------------------------------------------------

class TestEntradaAccumulation:

    async def test_create_task_succeeds_when_destination_has_same_product_below_limit(
        self, client, base_data, admin_token, db_session
    ):
        """
        entrada task onto a location that already holds the same product is OK
        when the product's units_per_location permits the new total.
        """
        worker = base_data["worker"]
        loc = base_data["location1"]
        product = base_data["product1"]
        product.units_per_location = 10
        db_session.add(product)
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=loc.id,
            product_id=product.id,
            quantity=3,
        ))
        await db_session.commit()

        with patch("app.api.tasks.websocket_service") as mock_ws:
            mock_ws.broadcast_task_assigned = AsyncMock()
            response = await client.post(
                "/tasks",
                headers=_auth(admin_token),
                json={
                    "assigned_to": str(worker.id),
                    "type": "entrada",
                    "destination_location_id": str(loc.id),
                    "product_id": str(product.id),
                    "quantity": 2,
                },
            )

        assert response.status_code == 201

    async def test_create_task_fails_when_destination_has_same_product_over_limit(
        self, client, base_data, admin_token, db_session
    ):
        worker = base_data["worker"]
        loc = base_data["location1"]
        product = base_data["product1"]
        product.units_per_location = 5
        db_session.add(product)
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=loc.id,
            product_id=product.id,
            quantity=4,
        ))
        await db_session.commit()

        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={
                "assigned_to": str(worker.id),
                "type": "entrada",
                "destination_location_id": str(loc.id),
                "product_id": str(product.id),
                "quantity": 3,  # 4 + 3 > 5
            },
        )
        assert response.status_code == 400
        assert "capacidad" in response.json()["detail"].lower()

    async def test_create_task_fails_when_product_does_not_allow_accumulation(
        self, client, base_data, admin_token, db_session
    ):
        """Same product but no units_per_location → cannot accumulate, returns 400."""
        worker = base_data["worker"]
        loc = base_data["location1"]
        product = base_data["product1"]
        # product.units_per_location stays None
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=loc.id,
            product_id=product.id,
            quantity=1,
        ))
        await db_session.commit()

        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={
                "assigned_to": str(worker.id),
                "type": "entrada",
                "destination_location_id": str(loc.id),
                "product_id": str(product.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 400
        assert "acumulación" in response.json()["detail"].lower()

    async def test_create_task_fails_when_quantity_exceeds_units_per_location_on_empty(
        self, client, base_data, admin_token, db_session
    ):
        """Empty destination, but the requested qty alone exceeds units_per_location."""
        worker = base_data["worker"]
        loc = base_data["location1"]
        product = base_data["product1"]
        product.units_per_location = 5
        db_session.add(product)
        await db_session.commit()

        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={
                "assigned_to": str(worker.id),
                "type": "entrada",
                "destination_location_id": str(loc.id),
                "product_id": str(product.id),
                "quantity": 6,
            },
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Tasks.salida / traslado with box-backed origin
# ---------------------------------------------------------------------------

class TestSalidaTrasladoBoxOrigin:

    async def test_salida_from_loose_origin_succeeds(
        self, client, base_data, admin_token, db_session
    ):
        worker = base_data["worker"]
        origin = base_data["location1"]
        product = base_data["product1"]
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=origin.id,
            product_id=product.id,
            quantity=1,
        ))
        await db_session.commit()

        with patch("app.api.tasks.websocket_service") as mock_ws:
            mock_ws.broadcast_task_assigned = AsyncMock()
            response = await client.post(
                "/tasks",
                headers=_auth(admin_token),
                json={
                    "assigned_to": str(worker.id),
                    "type": "salida",
                    "origin_location_id": str(origin.id),
                    "product_id": str(product.id),
                    "quantity": 1,
                },
            )
        assert response.status_code == 201

    async def test_salida_from_box_origin_quantity_exceeds_box_returns_400(
        self, client, base_data, admin_token, db_session
    ):
        worker = base_data["worker"]
        origin = base_data["location1"]
        product = base_data["product1"]
        box = base_data["box"]  # current_quantity=10
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=origin.id,
            product_id=None,
            box_id=box.id,
            quantity=None,
        ))
        await db_session.commit()

        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={
                "assigned_to": str(worker.id),
                "type": "salida",
                "origin_location_id": str(origin.id),
                "product_id": str(product.id),
                "quantity": 999,  # box only has 10
            },
        )
        assert response.status_code == 400
        assert "supera" in response.json()["detail"].lower()

    async def test_salida_product_mismatch_with_box_returns_400(
        self, client, base_data, admin_token, db_session
    ):
        worker = base_data["worker"]
        origin = base_data["location1"]
        wrong_product = base_data["product2"]  # box holds product1
        box = base_data["box"]
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=origin.id,
            product_id=None,
            box_id=box.id,
            quantity=None,
        ))
        await db_session.commit()

        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={
                "assigned_to": str(worker.id),
                "type": "salida",
                "origin_location_id": str(origin.id),
                "product_id": str(wrong_product.id),
                "quantity": 1,
            },
        )
        assert response.status_code == 400
        assert "no se encuentra" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Movements: partial / full salida from a Box
# ---------------------------------------------------------------------------

class TestSalidaFromBoxHttp:

    async def test_partial_salida_decrements_box_keeps_item(
        self, client, base_data, admin_token, db_session
    ):
        admin = base_data["admin"]
        worker = base_data["worker"]
        origin = base_data["location1"]
        box = base_data["box"]  # qty 10
        task_id = uuid.uuid4()
        db_session.add_all([
            Task(
                id=task_id,
                company_id=admin.company_id,
                created_by=admin.id,
                assigned_to=worker.id,
                type=TaskType.salida,
                origin_location_id=origin.id,
            ),
            InventoryItem(
                id=uuid.uuid4(),
                location_id=origin.id,
                product_id=None,
                box_id=box.id,
                quantity=None,
            ),
        ])
        await db_session.commit()

        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            response = await client.post(
                "/movements",
                headers=_auth(admin_token),
                json={
                    "task_id": str(task_id),
                    "type": "salida",
                    "origin_location_id": str(origin.id),
                    "product_id": str(base_data["product1"].id),
                    "quantity": 3,
                },
            )
        assert response.status_code == 201
        await db_session.refresh(box)
        assert box.current_quantity == 7
        # Item still in location
        item = (await db_session.execute(
            select(InventoryItem).where(InventoryItem.location_id == origin.id)
        )).scalar_one_or_none()
        assert item is not None

    async def test_full_salida_deletes_item(
        self, client, base_data, admin_token, db_session
    ):
        admin = base_data["admin"]
        worker = base_data["worker"]
        origin = base_data["location1"]
        box = base_data["box"]  # qty 10
        task_id = uuid.uuid4()
        db_session.add_all([
            Task(
                id=task_id,
                company_id=admin.company_id,
                created_by=admin.id,
                assigned_to=worker.id,
                type=TaskType.salida,
                origin_location_id=origin.id,
            ),
            InventoryItem(
                id=uuid.uuid4(),
                location_id=origin.id,
                product_id=None,
                box_id=box.id,
                quantity=None,
            ),
        ])
        await db_session.commit()

        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            response = await client.post(
                "/movements",
                headers=_auth(admin_token),
                json={
                    "task_id": str(task_id),
                    "type": "salida",
                    "origin_location_id": str(origin.id),
                    "product_id": str(base_data["product1"].id),
                    "quantity": 10,  # full
                },
            )
        assert response.status_code == 201
        item = (await db_session.execute(
            select(InventoryItem).where(InventoryItem.location_id == origin.id)
        )).scalar_one_or_none()
        assert item is None  # InventoryItem removed
