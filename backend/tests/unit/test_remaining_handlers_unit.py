"""
Direct-call unit tests for the remaining auth, movements, locations and
inventory handler branches. Mirrors what the integration suite exercises
through HTTP but invokes the coroutines directly, which is what coverage.py
actually traces.

Covered:
  auth.verify_email, auth.forgot_password, auth.reset_password
  locations.setup_location_inventory
  inventory.get_inventory, inventory.get_inventory_item
  movements.create_movement entrada/traslado/salida branches not covered
    by the existing test_inventory_service.py
"""

import io
import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.auth import verify_email, forgot_password, reset_password
from app.api.inventory import get_inventory, get_inventory_item
from app.api.locations import setup_location_inventory
from app.api.movements import create_movement
from app.models.models import (
    User, UserRole, InventoryItem, Product, Movement, MovementType,
)
from app.schemas.schemas import (
    ForgotPasswordRequest, ResetPasswordRequest,
    LocationInventorySetup, MovementCreate,
)
from app.core.security import get_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    return db


def _single(item):
    r = MagicMock()
    r.scalar_one_or_none.return_value = item
    return r


def _list(*items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = list(items)
    return r


def _admin(company_id=None):
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.company_id = company_id or uuid.uuid4()
    u.role = UserRole.admin
    return u


# ---------------------------------------------------------------------------
# verify_email
# ---------------------------------------------------------------------------

class TestVerifyEmailHandler:

    async def test_valid_token_marks_user_verified(self):
        db = _mock_db()
        user = MagicMock(spec=User)
        user.is_email_verified = False
        user.verification_token = "tok"
        db.execute.return_value = _single(user)

        result = await verify_email(token="tok", db=db)

        assert user.is_email_verified is True
        assert user.verification_token is None
        assert "verificado" in result["message"].lower()
        db.commit.assert_awaited_once()

    async def test_unknown_token_raises_400(self):
        db = _mock_db()
        db.execute.return_value = _single(None)
        with pytest.raises(HTTPException) as e:
            await verify_email(token="ghost", db=db)
        assert e.value.status_code == 400


# ---------------------------------------------------------------------------
# forgot_password / reset_password
# ---------------------------------------------------------------------------

class TestForgotPasswordHandler:

    async def test_unknown_email_returns_generic_message(self):
        db = _mock_db()
        db.execute.return_value = _single(None)
        result = await forgot_password(
            data=ForgotPasswordRequest(email="ghost@x.com"), db=db,
        )
        assert "si el email" in result["message"].lower()

    async def test_known_active_verified_email_assigns_token(self):
        db = _mock_db()
        user = MagicMock(spec=User)
        user.email = "a@a.com"
        user.name = "Anna"
        user.is_active = True
        user.is_email_verified = True
        db.execute.return_value = _single(user)

        # Email is auto-mocked by conftest; nothing else to patch
        result = await forgot_password(
            data=ForgotPasswordRequest(email="a@a.com"), db=db,
        )
        assert user.reset_password_token is not None
        assert user.reset_token_expires > datetime.utcnow()
        assert "si el email" in result["message"].lower()

    async def test_inactive_user_does_not_get_reset_token(self):
        db = _mock_db()
        user = MagicMock(spec=User)
        user.is_active = False
        user.is_email_verified = True
        user.reset_password_token = None
        db.execute.return_value = _single(user)

        await forgot_password(
            data=ForgotPasswordRequest(email="x@x.com"), db=db,
        )
        # Token was NOT set
        assert user.reset_password_token is None


class TestResetPasswordHandler:

    async def test_valid_token_resets_password(self):
        db = _mock_db()
        user = MagicMock(spec=User)
        user.reset_token_expires = datetime.utcnow() + timedelta(minutes=10)
        db.execute.return_value = _single(user)

        await reset_password(
            data=ResetPasswordRequest(token="t", new_password="long_enough_pw"),
            db=db,
        )
        assert user.password_hash is not None
        assert user.reset_password_token is None
        assert user.reset_token_expires is None
        assert user.must_change_password is False

    async def test_unknown_token_raises_400(self):
        db = _mock_db()
        db.execute.return_value = _single(None)
        with pytest.raises(HTTPException) as e:
            await reset_password(
                data=ResetPasswordRequest(token="x", new_password="long_enough_pw"),
                db=db,
            )
        assert e.value.status_code == 400

    async def test_expired_token_raises_400(self):
        db = _mock_db()
        user = MagicMock(spec=User)
        user.reset_token_expires = datetime.utcnow() - timedelta(seconds=1)
        db.execute.return_value = _single(user)

        with pytest.raises(HTTPException) as e:
            await reset_password(
                data=ResetPasswordRequest(token="x", new_password="long_enough_pw"),
                db=db,
            )
        assert e.value.status_code == 400

    async def test_short_password_raises_422(self):
        db = _mock_db()
        user = MagicMock(spec=User)
        user.reset_token_expires = datetime.utcnow() + timedelta(minutes=10)
        db.execute.return_value = _single(user)

        with pytest.raises(HTTPException) as e:
            await reset_password(
                data=ResetPasswordRequest(token="x", new_password="short"),
                db=db,
            )
        assert e.value.status_code == 422


# ---------------------------------------------------------------------------
# inventory.get_inventory / get_inventory_item
# ---------------------------------------------------------------------------

class TestInventoryHandlers:

    async def test_list_returns_company_items(self):
        db = _mock_db()
        item = MagicMock(spec=InventoryItem)
        db.execute.return_value = _list(item)

        result = await get_inventory(db=db, current_user=_admin())
        assert result == [item]

    async def test_get_item_returns_when_found(self):
        db = _mock_db()
        item = MagicMock(spec=InventoryItem)
        db.execute.return_value = _single(item)
        result = await get_inventory_item(item_id=uuid.uuid4(), db=db, current_user=_admin())
        assert result is item

    async def test_get_unknown_item_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)
        with pytest.raises(HTTPException) as e:
            await get_inventory_item(item_id=uuid.uuid4(), db=db, current_user=_admin())
        assert e.value.status_code == 404


# ---------------------------------------------------------------------------
# locations.setup_location_inventory
# ---------------------------------------------------------------------------

class TestLocationSetupHandler:

    async def test_setup_with_quantity_one_creates_loose_item(self):
        db = _mock_db()
        loc = MagicMock()
        product = MagicMock(spec=Product)
        product.id = uuid.uuid4()
        db.execute.side_effect = [
            _single(loc),       # location exists
            _single(None),      # location not occupied
            _single(product),   # product exists
        ]

        with patch("app.api.locations.websocket_service") as ws:
            ws.broadcast_movement_created = AsyncMock()
            result = await setup_location_inventory(
                location_id=uuid.uuid4(),
                data=LocationInventorySetup(product_id=product.id, quantity=1),
                db=db,
                current_user=_admin(),
            )
        assert result == {"success": True}
        db.commit.assert_awaited_once()

    async def test_setup_with_quantity_above_one_creates_single_item(self):
        """quantity>1 stores directly in InventoryItem.quantity — no Box created."""
        db = _mock_db()
        loc = MagicMock()
        product = MagicMock(spec=Product)
        product.id = uuid.uuid4()
        db.execute.side_effect = [
            _single(loc), _single(None), _single(product),
        ]

        with patch("app.api.locations.websocket_service") as ws:
            ws.broadcast_movement_created = AsyncMock()
            await setup_location_inventory(
                location_id=uuid.uuid4(),
                data=LocationInventorySetup(product_id=product.id, quantity=4),
                db=db,
                current_user=_admin(),
            )
        # Only one add: the InventoryItem itself (no intermediate Box)
        assert db.add.call_count == 1
        db.commit.assert_awaited_once()

    async def test_setup_unknown_location_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)
        with pytest.raises(HTTPException) as e:
            await setup_location_inventory(
                location_id=uuid.uuid4(),
                data=LocationInventorySetup(product_id=uuid.uuid4(), quantity=1),
                db=db,
                current_user=_admin(),
            )
        assert e.value.status_code == 404

    async def test_setup_occupied_location_raises_409(self):
        db = _mock_db()
        loc = MagicMock()
        existing = MagicMock(spec=InventoryItem)
        db.execute.side_effect = [_single(loc), _single(existing)]
        with pytest.raises(HTTPException) as e:
            await setup_location_inventory(
                location_id=uuid.uuid4(),
                data=LocationInventorySetup(product_id=uuid.uuid4(), quantity=1),
                db=db,
                current_user=_admin(),
            )
        assert e.value.status_code == 409

    async def test_setup_unknown_product_raises_404(self):
        db = _mock_db()
        loc = MagicMock()
        db.execute.side_effect = [_single(loc), _single(None), _single(None)]
        with pytest.raises(HTTPException) as e:
            await setup_location_inventory(
                location_id=uuid.uuid4(),
                data=LocationInventorySetup(product_id=uuid.uuid4(), quantity=1),
                db=db,
                current_user=_admin(),
            )
        assert e.value.status_code == 404


# ---------------------------------------------------------------------------
# movements: branches that the existing test_inventory_service.py misses
# ---------------------------------------------------------------------------

class TestCreateMovementBranches:

    def _user(self, company_id=None):
        u = MagicMock(spec=User)
        u.id = uuid.uuid4()
        u.company_id = company_id or uuid.uuid4()
        u.role = UserRole.worker
        return u

    async def test_entrada_without_destination_raises_400(self):
        db = _mock_db()
        user = self._user()
        with pytest.raises(HTTPException) as e:
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.entrada,
                    product_id=uuid.uuid4(),
                ),
                db, user,
            )
        assert e.value.status_code == 400

    async def test_movement_without_product_or_box_raises_400(self):
        db = _mock_db()
        with pytest.raises(HTTPException) as e:
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.entrada,
                    destination_location_id=uuid.uuid4(),
                ),
                db, self._user(),
            )
        assert e.value.status_code == 400

    async def test_entrada_empty_loc_quantity_one_loose_product(self):
        """quantity=1 onto an empty location stores the product directly."""
        db = _mock_db()
        user = self._user()
        db.execute.return_value = _single(None)  # destination empty

        with patch("app.api.movements.websocket_service") as ws:
            ws.broadcast_movement_created = AsyncMock()
            result = await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.entrada,
                    product_id=uuid.uuid4(),
                    destination_location_id=uuid.uuid4(),
                    quantity=1,
                ),
                db, user,
            )
        assert result.type == MovementType.entrada
        # No box created
        added_types = [type(c.args[0]).__name__ for c in db.add.call_args_list]
        assert "Box" not in added_types

    async def test_entrada_empty_loc_quantity_three_stores_quantity(self):
        """quantity>1 entrada onto empty location stores quantity directly on InventoryItem."""
        db = _mock_db()
        user = self._user()
        db.execute.side_effect = [
            _single(None),  # destination empty
            _single(None),  # product fetch returns None → no units_per_location check
        ]

        with patch("app.api.movements.websocket_service") as ws:
            ws.broadcast_movement_created = AsyncMock()
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.entrada,
                    product_id=uuid.uuid4(),
                    destination_location_id=uuid.uuid4(),
                    quantity=3,
                ),
                db, user,
            )
        # InventoryItem plus Movement = 2 adds (no Box)
        added_types = [type(c.args[0]).__name__ for c in db.add.call_args_list]
        assert "Box" not in added_types
        assert "InventoryItem" in added_types

    async def test_entrada_accumulation_succeeds_with_units_per_location(self):
        """entrada onto an occupied loc with same product + units_per_location."""
        db = _mock_db()
        user = self._user()
        product_id = uuid.uuid4()

        existing = MagicMock(spec=InventoryItem)
        existing.product_id = product_id
        existing.box_id = None
        existing.quantity = 2

        product = MagicMock(spec=Product)
        product.units_per_location = 10

        db.execute.side_effect = [
            _single(existing),  # destination occupied
            _single(product),   # product fetch
        ]

        with patch("app.api.movements.websocket_service") as ws:
            ws.broadcast_movement_created = AsyncMock()
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.entrada,
                    product_id=product_id,
                    destination_location_id=uuid.uuid4(),
                    quantity=3,
                ),
                db, user,
            )
        # accumulated to 5
        assert existing.quantity == 5

    async def test_entrada_capacity_exceeded_raises_400(self):
        db = _mock_db()
        user = self._user()
        product_id = uuid.uuid4()

        existing = MagicMock(spec=InventoryItem)
        existing.product_id = product_id
        existing.box_id = None
        existing.quantity = 9

        product = MagicMock(spec=Product)
        product.units_per_location = 10

        db.execute.side_effect = [_single(existing), _single(product)]

        with pytest.raises(HTTPException) as e:
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.entrada,
                    product_id=product_id,
                    destination_location_id=uuid.uuid4(),
                    quantity=5,
                ),
                db, user,
            )
        assert e.value.status_code == 400

    async def test_entrada_product_mismatch_raises_400(self):
        db = _mock_db()
        user = self._user()

        existing = MagicMock(spec=InventoryItem)
        existing.product_id = uuid.uuid4()  # different
        existing.box_id = None

        db.execute.return_value = _single(existing)

        with pytest.raises(HTTPException) as e:
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.entrada,
                    product_id=uuid.uuid4(),  # different
                    destination_location_id=uuid.uuid4(),
                    quantity=1,
                ),
                db, user,
            )
        assert e.value.status_code == 400

    async def test_traslado_without_locations_raises_400(self):
        db = _mock_db()
        with pytest.raises(HTTPException) as e:
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.traslado,
                    product_id=uuid.uuid4(),
                    origin_location_id=uuid.uuid4(),
                ),
                db, self._user(),
            )
        assert e.value.status_code == 400

    async def test_traslado_occupied_destination_raises_400(self):
        db = _mock_db()
        existing = MagicMock(spec=InventoryItem)
        db.execute.return_value = _single(existing)
        with pytest.raises(HTTPException) as e:
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.traslado,
                    product_id=uuid.uuid4(),
                    origin_location_id=uuid.uuid4(),
                    destination_location_id=uuid.uuid4(),
                ),
                db, self._user(),
            )
        assert e.value.status_code == 400

    async def test_traslado_origin_empty_raises_400(self):
        db = _mock_db()
        db.execute.side_effect = [_single(None), _single(None)]  # dest empty, origin empty
        with pytest.raises(HTTPException) as e:
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.traslado,
                    product_id=uuid.uuid4(),
                    origin_location_id=uuid.uuid4(),
                    destination_location_id=uuid.uuid4(),
                ),
                db, self._user(),
            )
        assert e.value.status_code == 400

    async def test_traslado_moves_item_to_destination(self):
        db = _mock_db()
        user = self._user()
        dest_id = uuid.uuid4()

        existing_item = MagicMock(spec=InventoryItem)
        existing_item.product_id = uuid.uuid4()
        existing_item.box_id = None
        existing_item.location_id = uuid.uuid4()

        db.execute.side_effect = [
            _single(None),         # destination empty
            _single(existing_item),# origin has item
        ]

        with patch("app.api.movements.websocket_service") as ws:
            ws.broadcast_movement_created = AsyncMock()
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.traslado,
                    product_id=existing_item.product_id,
                    origin_location_id=uuid.uuid4(),
                    destination_location_id=dest_id,
                ),
                db, user,
            )
        assert existing_item.location_id == dest_id

    async def test_salida_loose_product_deletes_item(self):
        db = _mock_db()
        user = self._user()

        item = MagicMock(spec=InventoryItem)
        item.product_id = uuid.uuid4()
        item.quantity = 1  # quantity_out == quantity → full exit → delete

        db.execute.return_value = _single(item)

        with patch("app.api.movements.websocket_service") as ws:
            ws.broadcast_movement_created = AsyncMock()
            await create_movement(
                MovementCreate(
                    task_id=uuid.uuid4(),
                    type=MovementType.salida,
                    product_id=item.product_id,
                    origin_location_id=uuid.uuid4(),
                    quantity=1,
                ),
                db, user,
            )
        db.delete.assert_awaited_once_with(item)
