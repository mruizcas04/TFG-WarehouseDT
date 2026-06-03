"""
Unit tests for inventory-related business logic in app/api/movements.py.

Covers:
  1. _inventory_to_dict pure helper
  2. create_movement handler for entrada / salida / traslado, called directly
     with a fully-mocked AsyncSession (no real DB).

Pattern: Arrange → Act → Assert
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.movements import _inventory_to_dict, create_movement
from app.models.models import InventoryItem, User, UserRole, MovementType
from app.schemas.schemas import MovementCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(company_id=None):
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.company_id = company_id or uuid.uuid4()
    user.role = UserRole.worker
    return user


def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Pure helper: _inventory_to_dict
# ---------------------------------------------------------------------------

class TestInventoryHelpers:

    def test_returns_none_for_empty_location(self):
        assert _inventory_to_dict(None) is None

    def test_with_direct_product_returns_correct_fields(self):
        item = MagicMock(spec=InventoryItem)
        item.id = uuid.uuid4()
        item.product_id = uuid.uuid4()
        item.quantity = 5

        result = _inventory_to_dict(item)

        assert result is not None
        assert result["id"] == str(item.id)
        assert result["product_id"] == str(item.product_id)
        assert result["quantity"] == 5

    def test_returns_dict_with_exactly_three_keys(self):
        """_inventory_to_dict must only expose id, product_id, quantity."""
        item = MagicMock(spec=InventoryItem)
        item.id = uuid.uuid4()
        item.product_id = uuid.uuid4()
        item.quantity = 1

        result = _inventory_to_dict(item)

        assert set(result.keys()) == {"id", "product_id", "quantity"}


# ---------------------------------------------------------------------------
# create_movement: entrada
# ---------------------------------------------------------------------------

class TestInventoryCreation:

    async def test_entrada_creates_item_in_empty_location(self):
        db = _mock_db()
        user = _make_user()
        location_id = uuid.uuid4()
        product_id = uuid.uuid4()

        db.execute.return_value = MagicMock(**{"scalar_one_or_none.return_value": None})

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.entrada,
            product_id=product_id,
            destination_location_id=location_id,
            quantity=1,
        )

        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            result = await create_movement(movement_data, db, user)

        assert db.add.called
        db.commit.assert_awaited_once()
        assert result.type == MovementType.entrada

    async def test_entrada_to_occupied_location_with_different_product_raises_400(self):
        db = _mock_db()
        user = _make_user()
        location_id = uuid.uuid4()

        existing_item = MagicMock(spec=InventoryItem)
        existing_item.product_id = uuid.uuid4()   # different from incoming
        db.execute.return_value = MagicMock(
            **{"scalar_one_or_none.return_value": existing_item}
        )

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.entrada,
            product_id=uuid.uuid4(),
            destination_location_id=location_id,
            quantity=1,
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_movement(movement_data, db, user)
        assert exc_info.value.status_code == 400
        assert "producto diferente" in exc_info.value.detail

    async def test_partial_salida_decrements_item_quantity(self):
        """
        A salida with quantity < item.quantity must subtract from item.quantity
        and leave the InventoryItem in the DB.
        """
        db = _mock_db()
        user = _make_user()
        origin_id = uuid.uuid4()

        item = MagicMock(spec=InventoryItem)
        item.product_id = uuid.uuid4()
        item.quantity = 10

        db.execute.return_value = MagicMock(**{"scalar_one_or_none.return_value": item})

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.salida,
            product_id=item.product_id,
            origin_location_id=origin_id,
            quantity=3,
        )

        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            await create_movement(movement_data, db, user)

        assert item.quantity == 7
        db.delete.assert_not_called()

    async def test_full_salida_deletes_inventory_item(self):
        """
        A salida with quantity >= item.quantity must delete the InventoryItem
        leaving the location free.
        """
        db = _mock_db()
        user = _make_user()
        origin_id = uuid.uuid4()

        item = MagicMock(spec=InventoryItem)
        item.product_id = uuid.uuid4()
        item.quantity = 5

        db.execute.return_value = MagicMock(**{"scalar_one_or_none.return_value": item})

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.salida,
            product_id=item.product_id,
            origin_location_id=origin_id,
            quantity=5,
        )

        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            await create_movement(movement_data, db, user)

        db.delete.assert_awaited_once_with(item)

    async def test_traslado_moves_item_to_destination(self):
        db = _mock_db()
        user = _make_user()
        origin_id = uuid.uuid4()
        dest_id = uuid.uuid4()

        item = MagicMock(spec=InventoryItem)
        item.product_id = uuid.uuid4()
        item.quantity = 2

        db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": None}),  # dest free
            MagicMock(**{"scalar_one_or_none.return_value": item}),  # origin item
        ]

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.traslado,
            product_id=item.product_id,
            origin_location_id=origin_id,
            destination_location_id=dest_id,
            quantity=2,
        )

        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            await create_movement(movement_data, db, user)

        assert item.location_id == dest_id
