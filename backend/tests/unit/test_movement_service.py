"""
Unit tests for movement validation and registration logic.

The business rules tested here (app/api/movements.py — create_movement handler):

  - Entrada:  destination required, origin must be None / not validated.
  - Salida:   origin required, destination must be None / not validated.
  - Traslado: both origin AND destination required; origin must not be empty;
              destination must be free.

The WebSocket broadcast that follows every successful movement is also verified.

All DB access is fully mocked with AsyncMock; no SQLite or PostgreSQL involved.

Pattern: Arrange → Act → Assert
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from fastapi import HTTPException

from app.api.movements import create_movement
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
# Traslado validations
# ---------------------------------------------------------------------------

class TestTransferValidations:

    async def test_validate_transfer_with_empty_origin(self):
        """
        A traslado whose origin location has no inventory must raise HTTP 400
        with the detail message "No hay inventario en la ubicación de origen".
        Moving from an empty shelf makes no sense and must be rejected.
        """
        # Arrange
        db = _mock_db()
        user = _make_user()
        origin_id = uuid.uuid4()
        dest_id = uuid.uuid4()

        db.execute.side_effect = [
            # Destination is empty (OK to receive)
            MagicMock(**{"scalar_one_or_none.return_value": None}),
            # Origin is also empty → validation error
            MagicMock(**{"scalar_one_or_none.return_value": None}),
        ]

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.traslado,
            product_id=uuid.uuid4(),
            origin_location_id=origin_id,
            destination_location_id=dest_id,
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_movement(movement_data, db, user)
        assert exc_info.value.status_code == 400
        assert "No hay inventario" in exc_info.value.detail

    async def test_validate_transfer_with_occupied_destination(self):
        """
        A traslado targeting an already-occupied destination must raise HTTP 400.
        Two InventoryItems cannot occupy the same Location simultaneously.
        """
        # Arrange
        db = _mock_db()
        user = _make_user()

        existing_item = MagicMock(spec=InventoryItem)
        # First execute: destination check → occupied
        db.execute.return_value = MagicMock(
            **{"scalar_one_or_none.return_value": existing_item}
        )

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.traslado,
            product_id=uuid.uuid4(),
            origin_location_id=uuid.uuid4(),
            destination_location_id=uuid.uuid4(),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_movement(movement_data, db, user)
        assert exc_info.value.status_code == 400
        assert "destino" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Entrada validation: origin is not required
# ---------------------------------------------------------------------------

class TestEntradaValidation:

    async def test_validate_entry_without_origin_is_valid(self):
        """
        An entrada movement with origin_location_id=None must succeed.
        Goods arriving at the warehouse have no prior internal location.
        The handler must NOT raise an exception for a missing origin.
        """
        # Arrange
        db = _mock_db()
        user = _make_user()
        dest_id = uuid.uuid4()
        product_id = uuid.uuid4()

        # Destination is free
        db.execute.return_value = MagicMock(**{"scalar_one_or_none.return_value": None})

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.entrada,
            product_id=product_id,
            origin_location_id=None,     # no origin — this is the key assertion
            destination_location_id=dest_id,
            quantity=1,
        )

        # Act — must not raise
        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            result = await create_movement(movement_data, db, user)

        # Assert: movement created and committed
        db.commit.assert_awaited_once()
        assert result.type == MovementType.entrada


# ---------------------------------------------------------------------------
# Salida validation: destination is not required
# ---------------------------------------------------------------------------

class TestSalidaValidation:

    async def test_validate_exit_without_destination_is_valid(self):
        """
        A salida movement with destination_location_id=None must succeed.
        Goods leaving the warehouse have no internal destination.
        The handler must NOT raise an exception for a missing destination.
        """
        # Arrange
        db = _mock_db()
        user = _make_user()
        origin_id = uuid.uuid4()

        # Item at origin: standalone product
        item = MagicMock(spec=InventoryItem)
        item.product_id = uuid.uuid4()
        item.quantity = 5

        db.execute.return_value = MagicMock(
            **{"scalar_one_or_none.return_value": item}
        )

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.salida,
            product_id=item.product_id,
            origin_location_id=origin_id,
            destination_location_id=None,   # no destination — this is the key assertion
        )

        # Act — must not raise
        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            result = await create_movement(movement_data, db, user)

        # Assert: item deleted (full exit of standalone product) and movement committed
        db.delete.assert_awaited_once_with(item)
        db.commit.assert_awaited_once()
        assert result.type == MovementType.salida


# ---------------------------------------------------------------------------
# WebSocket broadcast
# ---------------------------------------------------------------------------

class TestWebSocketBroadcast:

    async def test_register_movement_calls_websocket_broadcast(self):
        """
        Every successful movement registration must call
        websocket_service.broadcast_movement_created exactly once.
        This ensures the digital twin (Unity) receives real-time updates.
        """
        # Arrange
        db = _mock_db()
        user = _make_user()
        dest_id = uuid.uuid4()
        product_id = uuid.uuid4()

        db.execute.return_value = MagicMock(**{"scalar_one_or_none.return_value": None})

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.entrada,
            product_id=product_id,
            destination_location_id=dest_id,
            quantity=1,
        )

        # Act
        with patch("app.api.movements.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            await create_movement(movement_data, db, user)

        # Assert: broadcast called exactly once with keyword args
        mock_ws.broadcast_movement_created.assert_awaited_once()
        call_kwargs = mock_ws.broadcast_movement_created.call_args.kwargs
        assert "movement_id" in call_kwargs
        assert "data" in call_kwargs

    async def test_movement_without_product_raises_400(self):
        """
        A movement with product_id=None must be rejected with HTTP 400
        before any DB query.
        """
        db = _mock_db()
        user = _make_user()

        movement_data = MovementCreate(
            task_id=uuid.uuid4(),
            type=MovementType.entrada,
            product_id=None,
            destination_location_id=uuid.uuid4(),
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_movement(movement_data, db, user)
        assert exc_info.value.status_code == 400
        db.execute.assert_not_called()
