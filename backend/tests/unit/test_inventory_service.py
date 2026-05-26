"""
Unit tests for inventory-related business logic.

Since the project has no dedicated inventory service, all inventory mutations
happen inside the movement router (app/api/movements.py).  These tests target:

  1. The pure helper function _inventory_to_dict — no mocking needed,
     it receives plain Python objects.
  2. The create_movement handler for entrada/salida movements, called directly
     with a fully-mocked AsyncSession so no real DB is involved.

Pattern: Arrange → Act → Assert
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.movements import _inventory_to_dict, create_movement
from app.models.models import InventoryItem, Box, User, UserRole, MovementType
from app.schemas.schemas import MovementCreate


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

def _make_user(company_id=None):
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.company_id = company_id or uuid.uuid4()
    user.role = UserRole.worker
    return user


def _mock_db():
    """AsyncMock that satisfies the AsyncSession interface used by create_movement."""
    db = AsyncMock()
    db.add = MagicMock()          # synchronous in real SQLAlchemy
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------

class TestInventoryHelpers:

    def test_inventory_to_dict_returns_none_for_empty_location(self):
        """
        _inventory_to_dict(None) must return None.
        A None item represents a free location.
        """
        # Act & Assert
        assert _inventory_to_dict(None) is None

    def test_inventory_to_dict_with_direct_product(self):
        """
        When an InventoryItem references a Product directly (no Box),
        _inventory_to_dict must expose product_id and use item.quantity.
        """
        # Arrange
        item = MagicMock(spec=InventoryItem)
        item.id = uuid.uuid4()
        item.product_id = uuid.uuid4()
        item.box_id = None
        item.quantity = 5

        # Act
        result = _inventory_to_dict(item)

        # Assert
        assert result is not None
        assert result["product_id"] == str(item.product_id)
        assert result["box_id"] is None
        assert result["quantity"] == 5
        assert result["box_current_quantity"] is None

    def test_inventory_to_dict_with_box_uses_box_quantity(self):
        """
        When an InventoryItem references a Box, _inventory_to_dict must derive
        quantity from box.current_quantity, not from item.quantity.
        This models the rule that a Box tracks its own fill level.
        """
        # Arrange
        item = MagicMock(spec=InventoryItem)
        item.id = uuid.uuid4()
        item.product_id = None
        item.box_id = uuid.uuid4()
        item.quantity = None

        box = MagicMock(spec=Box)
        box.current_quantity = 12
        box.max_capacity = 20

        # Act
        result = _inventory_to_dict(item, box)

        # Assert
        assert result["box_id"] == str(item.box_id)
        assert result["quantity"] == 12
        assert result["box_current_quantity"] == 12
        assert result["box_max_capacity"] == 20

    def test_item_cannot_reference_both_product_and_box(self):
        """
        Business rule: an InventoryItem references a Product OR a Box, never both.

        The handler enforces this implicitly: when product_id is set, _inventory_to_dict
        reads item.quantity (not box quantity), and box_current_quantity is None.
        A valid item with both fields set would be treated as a product item — the
        box information is silently ignored, which signals a data-integrity bug.

        This test documents the expected behaviour so any future change to the helper
        that starts using box_id when product_id is also set will be caught.
        """
        # Arrange: item with both fields set (invalid state per business rules)
        item = MagicMock(spec=InventoryItem)
        item.id = uuid.uuid4()
        item.product_id = uuid.uuid4()  # product_id is set …
        item.box_id = uuid.uuid4()      # … AND box_id is also set (invalid)
        item.quantity = 3

        # Act
        result = _inventory_to_dict(item)  # no Box object passed

        # Assert: product_id branch is taken; box_current_quantity stays None
        assert result["product_id"] == str(item.product_id)
        assert result["quantity"] == 3
        assert result["box_current_quantity"] is None


# ---------------------------------------------------------------------------
# Inventory creation: entrada movement handler
# ---------------------------------------------------------------------------

class TestInventoryCreation:

    async def test_create_inventory_item_in_empty_location(self):
        """
        An entrada movement targeting an empty location must succeed:
        db.add is called to persist the new InventoryItem, and the
        returned movement has type=entrada.
        """
        # Arrange
        db = _mock_db()
        user = _make_user()
        location_id = uuid.uuid4()
        product_id = uuid.uuid4()

        # DB: no existing inventory at the destination
        db.execute.return_value = MagicMock(**{"scalar_one_or_none.return_value": None})

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.entrada,
            product_id=product_id,
            destination_location_id=location_id,
            quantity=1,
        )

        # Act
        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            result = await create_movement(movement_data, db, user)

        # Assert
        assert db.add.called, "InventoryItem and Movement must be added to the session"
        db.commit.assert_awaited_once()
        assert result.type == MovementType.entrada

    async def test_create_inventory_item_in_occupied_location(self):
        """
        An entrada movement to an already-occupied location must raise HTTP 400.
        This prevents two InventoryItems from sharing the same Location
        (business rule: one location → at most one InventoryItem).
        """
        # Arrange
        db = _mock_db()
        user = _make_user()
        location_id = uuid.uuid4()

        existing_item = MagicMock(spec=InventoryItem)
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

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_movement(movement_data, db, user)
        assert exc_info.value.status_code == 400
        # Error message changed when product-mismatch check was added: the
        # occupied-location guard now rejects with "ya contiene un producto
        # diferente" because the mocked existing item has product_id=None,
        # which does not match the incoming product_id.
        assert "producto diferente" in exc_info.value.detail

    async def test_update_quantity_of_existing_box_item_on_partial_exit(self):
        """
        A partial salida (quantity < box.current_quantity) must decrement
        box.current_quantity without deleting the InventoryItem.
        The location remains occupied after the exit.
        """
        # Arrange
        db = _mock_db()
        user = _make_user()
        origin_id = uuid.uuid4()

        box = MagicMock(spec=Box)
        box.id = uuid.uuid4()
        box.current_quantity = 10
        box.max_capacity = 20

        item = MagicMock(spec=InventoryItem)
        item.box_id = box.id
        item.product_id = None

        db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": item}),  # InventoryItem
            MagicMock(**{"scalar_one_or_none.return_value": box}),   # Box
        ]

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.salida,
            origin_location_id=origin_id,
            quantity=3,
        )

        # Act
        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            await create_movement(movement_data, db, user)

        # Assert: box quantity reduced; item still in the DB (delete not called)
        assert box.current_quantity == 7
        db.delete.assert_not_called()

    async def test_delete_inventory_item_on_full_exit(self):
        """
        A complete salida (quantity equals the full box contents) must delete
        the InventoryItem so the location is left free.
        """
        # Arrange
        db = _mock_db()
        user = _make_user()
        origin_id = uuid.uuid4()

        box = MagicMock(spec=Box)
        box.id = uuid.uuid4()
        box.current_quantity = 5
        box.max_capacity = 20

        item = MagicMock(spec=InventoryItem)
        item.box_id = box.id
        item.product_id = None

        db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": item}),
            MagicMock(**{"scalar_one_or_none.return_value": box}),
        ]

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.salida,
            origin_location_id=origin_id,
            quantity=5,  # equals box.current_quantity → full exit
        )

        # Act
        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            await create_movement(movement_data, db, user)

        # Assert: InventoryItem was deleted, leaving the location free
        db.delete.assert_awaited_once_with(item)
