"""
Unit tests for warehouse handler functions (app/api/warehouses.py).

Every handler is called directly with a mocked AsyncSession and a mock
current_user — no HTTP stack, no ASGI transport.  This ensures that
coverage.py traces the function bodies, which fixes the sys.monitoring
gap observed when going through httpx's ASGITransport.

Pattern: Arrange → Act → Assert
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.warehouses import (
    get_warehouses,
    create_warehouse,
    get_warehouse,
    get_warehouse_full,
    expand_warehouse,
    update_warehouse,
    delete_warehouse,
)
from app.models.models import Warehouse, Shelf, Level, Location, InventoryItem, Task, TaskStatus, TaskType
from app.schemas.schemas import (
    WarehouseCreate, AisleConfig, ShelfConfig, WarehouseNameUpdate,
    WarehouseExpand, ExtendAisleConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


def _mock_user(company_id=None):
    user = MagicMock()
    user.company_id = company_id or uuid.uuid4()
    return user


def _make_result_single(item):
    """Return a mock execute result where scalar_one_or_none() returns item."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = item
    r.scalars.return_value.all.return_value = [item] if item is not None else []
    return r


def _make_result_list(*items):
    """Return a mock execute result where scalars().all() returns items."""
    r = MagicMock()
    r.scalars.return_value.all.return_value = list(items)
    return r


# ---------------------------------------------------------------------------
# get_warehouses
# ---------------------------------------------------------------------------

class TestGetWarehouses:

    async def test_returns_list_of_warehouses_for_company(self):
        """get_warehouses must return all warehouses belonging to the current user's company."""
        db = _mock_db()
        user = _mock_user()
        mock_wh = MagicMock(spec=Warehouse)
        db.execute.return_value = _make_result_list(mock_wh)

        result = await get_warehouses(db=db, current_user=user)

        db.execute.assert_awaited_once()
        assert len(result) == 1

    async def test_returns_empty_list_when_no_warehouses(self):
        """get_warehouses returns an empty list when the company has no warehouses."""
        db = _mock_db()
        user = _mock_user()
        db.execute.return_value = _make_result_list()

        result = await get_warehouses(db=db, current_user=user)

        assert result == []


# ---------------------------------------------------------------------------
# create_warehouse
# ---------------------------------------------------------------------------

class TestCreateWarehouse:

    async def test_creates_warehouse_with_full_hierarchy(self):
        """
        create_warehouse must persist a Warehouse plus Shelf/Level/Location objects
        matching the aisles configuration and return the warehouse.
        """
        db = _mock_db()
        user = _mock_user()

        warehouse_data = WarehouseCreate(
            name="Unit Warehouse",
            aisles=[
                AisleConfig(shelves=[ShelfConfig(num_levels=2, num_locations=3)])
            ],
        )

        result = await create_warehouse(warehouse_data=warehouse_data, db=db, current_user=user)

        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()
        assert result.name == "Unit Warehouse"
        assert result.num_shelves == 1
        assert result.total_locations == 6  # 2 levels * 3 locations

    async def test_creates_multiple_aisles(self):
        """create_warehouse with multiple aisles must count shelves and locations correctly."""
        db = _mock_db()
        user = _mock_user()

        warehouse_data = WarehouseCreate(
            name="Big Warehouse",
            aisles=[
                AisleConfig(shelves=[ShelfConfig(num_levels=1, num_locations=2)]),
                AisleConfig(shelves=[ShelfConfig(num_levels=1, num_locations=2)]),
            ],
        )

        result = await create_warehouse(warehouse_data=warehouse_data, db=db, current_user=user)

        assert result.num_shelves == 2
        assert result.total_locations == 4

    async def test_creates_double_shelf_generates_back_aisle(self):
        """
        create_warehouse with is_double=True must generate a mirrored back shelf
        in a separate aisle (the branch at lines 77-91 of warehouses.py).
        """
        db = _mock_db()
        user = _mock_user()

        warehouse_data = WarehouseCreate(
            name="Double Warehouse",
            aisles=[
                AisleConfig(shelves=[ShelfConfig(num_levels=2, num_locations=3, is_double=True)])
            ],
        )

        result = await create_warehouse(warehouse_data=warehouse_data, db=db, current_user=user)

        # is_double counts as 2 shelf rows
        assert result.num_shelves == 2
        # 2 sides × 2 levels × 3 locations = 12
        assert result.total_locations == 12
        db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_warehouse
# ---------------------------------------------------------------------------

class TestGetWarehouse:

    async def test_found_returns_warehouse(self):
        """get_warehouse returns the warehouse when it exists and belongs to the company."""
        db = _mock_db()
        user = _mock_user()
        wh_id = uuid.uuid4()
        mock_wh = MagicMock(spec=Warehouse)
        mock_wh.id = wh_id
        db.execute.return_value = _make_result_single(mock_wh)

        result = await get_warehouse(warehouse_id=wh_id, db=db, current_user=user)

        assert result is mock_wh

    async def test_not_found_raises_404(self):
        """get_warehouse raises HTTP 404 when the warehouse is not found."""
        db = _mock_db()
        user = _mock_user()
        db.execute.return_value = _make_result_single(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_warehouse(warehouse_id=uuid.uuid4(), db=db, current_user=user)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_warehouse_full
# ---------------------------------------------------------------------------

class TestGetWarehouseFull:

    async def test_not_found_raises_404(self):
        """get_warehouse_full raises HTTP 404 when the warehouse does not exist."""
        db = _mock_db()
        user = _mock_user()
        db.execute.return_value = _make_result_single(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_warehouse_full(warehouse_id=uuid.uuid4(), db=db, current_user=user)

        assert exc_info.value.status_code == 404

    async def test_empty_warehouse_returns_nested_response(self):
        """
        get_warehouse_full for a warehouse with no shelves returns a WarehouseFullResponse
        with an empty shelves list and no active task locations.
        """
        db = _mock_db()
        company_id = uuid.uuid4()
        user = _mock_user(company_id=company_id)
        warehouse_id = uuid.uuid4()

        mock_wh = MagicMock()
        mock_wh.id = warehouse_id
        mock_wh.name = "Empty Warehouse"
        mock_wh.num_shelves = 0
        mock_wh.num_levels = None
        mock_wh.num_locations = None
        mock_wh.total_locations = 0
        mock_wh.created_at = datetime(2024, 1, 1)

        db.execute.side_effect = [
            _make_result_single(mock_wh),  # get warehouse
            _make_result_list(),           # get shelves
            _make_result_list(),           # get levels
            _make_result_list(),           # get locations
            _make_result_list(),           # get inventory
            _make_result_list(),           # get active tasks
        ]

        result = await get_warehouse_full(warehouse_id=warehouse_id, db=db, current_user=user)

        assert result.id == warehouse_id
        assert result.shelves == []
        assert result.active_task_locations == []

    async def test_warehouse_with_hierarchy_and_no_inventory(self):
        """
        get_warehouse_full builds the complete shelf/level/location tree when
        shelves, levels and locations exist but no inventory is present.
        """
        db = _mock_db()
        company_id = uuid.uuid4()
        user = _mock_user(company_id=company_id)
        warehouse_id = uuid.uuid4()
        shelf_id = uuid.uuid4()
        level_id = uuid.uuid4()
        loc1_id = uuid.uuid4()
        loc2_id = uuid.uuid4()

        mock_wh = MagicMock()
        mock_wh.id = warehouse_id
        mock_wh.name = "Full Warehouse"
        mock_wh.num_shelves = 1
        mock_wh.num_levels = None
        mock_wh.num_locations = None
        mock_wh.total_locations = 2
        mock_wh.created_at = datetime(2024, 1, 1)

        mock_shelf = MagicMock()
        mock_shelf.id = shelf_id
        mock_shelf.aisle_number = 1
        mock_shelf.shelf_number = 1

        mock_level = MagicMock()
        mock_level.id = level_id
        mock_level.shelf_id = shelf_id
        mock_level.level_number = 1

        mock_loc1 = MagicMock()
        mock_loc1.id = loc1_id
        mock_loc1.level_id = level_id
        mock_loc1.position_number = 1
        mock_loc1.nfc_tag = None

        mock_loc2 = MagicMock()
        mock_loc2.id = loc2_id
        mock_loc2.level_id = level_id
        mock_loc2.position_number = 2
        mock_loc2.nfc_tag = "NFC-001"

        db.execute.side_effect = [
            _make_result_single(mock_wh),           # get warehouse
            _make_result_list(mock_shelf),          # get shelves
            _make_result_list(mock_level),          # get levels
            _make_result_list(mock_loc1, mock_loc2),# get locations
            _make_result_list(),                    # get inventory (empty)
            _make_result_list(),                    # get active tasks
        ]

        result = await get_warehouse_full(warehouse_id=warehouse_id, db=db, current_user=user)

        assert len(result.shelves) == 1
        shelf_resp = result.shelves[0]
        assert len(shelf_resp.levels) == 1
        assert len(shelf_resp.levels[0].locations) == 2
        for loc in shelf_resp.levels[0].locations:
            assert loc.inventory is None

    async def test_warehouse_with_inventory_shows_in_location(self):
        """
        get_warehouse_full populates the inventory field of a location that
        has a product-based InventoryItem linked to it.
        """
        db = _mock_db()
        company_id = uuid.uuid4()
        user = _mock_user(company_id=company_id)
        warehouse_id = uuid.uuid4()
        shelf_id = uuid.uuid4()
        level_id = uuid.uuid4()
        loc_id = uuid.uuid4()
        item_id = uuid.uuid4()
        product_id = uuid.uuid4()

        mock_wh = MagicMock()
        mock_wh.id = warehouse_id
        mock_wh.name = "Occupied Warehouse"
        mock_wh.num_shelves = 1
        mock_wh.num_levels = None
        mock_wh.num_locations = None
        mock_wh.total_locations = 1
        mock_wh.created_at = datetime(2024, 1, 1)

        mock_shelf = MagicMock()
        mock_shelf.id = shelf_id
        mock_shelf.aisle_number = 1
        mock_shelf.shelf_number = 1

        mock_level = MagicMock()
        mock_level.id = level_id
        mock_level.shelf_id = shelf_id
        mock_level.level_number = 1

        mock_loc = MagicMock()
        mock_loc.id = loc_id
        mock_loc.level_id = level_id
        mock_loc.position_number = 1
        mock_loc.nfc_tag = None

        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.location_id = loc_id
        mock_item.product_id = product_id
        mock_item.box_id = None
        mock_item.quantity = 7

        mock_product = MagicMock()
        mock_product.id = product_id
        mock_product.name = "Widget"
        mock_product.barcode = "BAR-W-001"
        mock_product.category_id = None  # avoids the categories query

        db.execute.side_effect = [
            _make_result_single(mock_wh),        # get warehouse
            _make_result_list(mock_shelf),       # get shelves
            _make_result_list(mock_level),       # get levels
            _make_result_list(mock_loc),         # get locations
            _make_result_list(mock_item),        # get inventory
            _make_result_list(mock_product),     # get products (direct_product_ids non-empty)
            _make_result_list(),                 # get active tasks
        ]

        result = await get_warehouse_full(warehouse_id=warehouse_id, db=db, current_user=user)

        loc_resp = result.shelves[0].levels[0].locations[0]
        assert loc_resp.inventory is not None
        assert loc_resp.inventory.quantity == 7
        assert loc_resp.inventory.product_id == product_id

    async def test_warehouse_with_inventory_with_category(self):
        """
        get_warehouse_full fetches categories when a product has category_id set
        (the branch at lines 165-166 of warehouses.py).
        """
        db = _mock_db()
        company_id = uuid.uuid4()
        user = _mock_user(company_id=company_id)
        warehouse_id = uuid.uuid4()
        shelf_id, level_id, loc_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        item_id, product_id, category_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        mock_wh = MagicMock()
        mock_wh.id = warehouse_id
        mock_wh.name = "Cat Warehouse"
        mock_wh.num_shelves = 1
        mock_wh.num_levels = None
        mock_wh.num_locations = None
        mock_wh.total_locations = 1
        mock_wh.created_at = datetime(2024, 1, 1)

        mock_shelf = MagicMock(); mock_shelf.id = shelf_id; mock_shelf.aisle_number = 1; mock_shelf.shelf_number = 1
        mock_level = MagicMock(); mock_level.id = level_id; mock_level.shelf_id = shelf_id; mock_level.level_number = 1
        mock_loc = MagicMock(); mock_loc.id = loc_id; mock_loc.level_id = level_id; mock_loc.position_number = 1; mock_loc.nfc_tag = None

        mock_item = MagicMock(); mock_item.id = item_id; mock_item.location_id = loc_id
        mock_item.product_id = product_id; mock_item.quantity = 3

        mock_product = MagicMock(); mock_product.id = product_id; mock_product.name = "Widget"
        mock_product.barcode = "BAR-001"; mock_product.category_id = category_id

        mock_cat = MagicMock(); mock_cat.id = category_id; mock_cat.name = "Electronics"; mock_cat.color = "#FF0000"

        db.execute.side_effect = [
            _make_result_single(mock_wh),
            _make_result_list(mock_shelf),
            _make_result_list(mock_level),
            _make_result_list(mock_loc),
            _make_result_list(mock_item),
            _make_result_list(mock_product),
            _make_result_list(mock_cat),   # categories query — the branch being tested
            _make_result_list(),           # active tasks
        ]

        result = await get_warehouse_full(warehouse_id=warehouse_id, db=db, current_user=user)

        inv = result.shelves[0].levels[0].locations[0].inventory
        assert inv is not None
        assert inv.product_category == "Electronics"
        assert inv.product_category_color == "#FF0000"

    async def test_warehouse_full_task_with_origin_location_populates_task_info(self):
        """
        When a task has origin_location_id set, active_task_info must include
        that location (branch at line 235 of warehouses.py).
        """
        db = _mock_db()
        company_id = uuid.uuid4()
        user = _mock_user(company_id=company_id)
        warehouse_id = uuid.uuid4()
        shelf_id, level_id, loc_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        mock_wh = MagicMock()
        mock_wh.id = warehouse_id; mock_wh.name = "W"; mock_wh.num_shelves = 1
        mock_wh.num_levels = None; mock_wh.num_locations = None; mock_wh.total_locations = 1
        mock_wh.created_at = datetime(2024, 1, 1)

        mock_shelf = MagicMock(); mock_shelf.id = shelf_id; mock_shelf.aisle_number = 1; mock_shelf.shelf_number = 1
        mock_level = MagicMock(); mock_level.id = level_id; mock_level.shelf_id = shelf_id; mock_level.level_number = 1
        mock_loc = MagicMock(); mock_loc.id = loc_id; mock_loc.level_id = level_id; mock_loc.position_number = 1; mock_loc.nfc_tag = None

        mock_task = MagicMock()
        mock_task.origin_location_id = loc_id       # ← covered branch
        mock_task.destination_location_id = None
        mock_task.type = MagicMock(value="salida")

        db.execute.side_effect = [
            _make_result_single(mock_wh),
            _make_result_list(mock_shelf),
            _make_result_list(mock_level),
            _make_result_list(mock_loc),
            _make_result_list(),           # no inventory
            _make_result_list(mock_task),  # active task with origin
        ]

        result = await get_warehouse_full(warehouse_id=warehouse_id, db=db, current_user=user)

        assert str(loc_id) in result.active_task_locations
        assert result.active_task_info[str(loc_id)] == "salida"

    async def test_warehouse_with_active_tasks_populates_task_info(self):
        """
        get_warehouse_full builds active_task_locations and active_task_info from
        pending and in-progress tasks linked to locations in this warehouse.
        """
        db = _mock_db()
        company_id = uuid.uuid4()
        user = _mock_user(company_id=company_id)
        warehouse_id = uuid.uuid4()
        shelf_id = uuid.uuid4()
        level_id = uuid.uuid4()
        loc_id = uuid.uuid4()

        mock_wh = MagicMock()
        mock_wh.id = warehouse_id
        mock_wh.name = "Active Warehouse"
        mock_wh.num_shelves = 1
        mock_wh.num_levels = None
        mock_wh.num_locations = None
        mock_wh.total_locations = 1
        mock_wh.created_at = datetime(2024, 1, 1)

        mock_shelf = MagicMock()
        mock_shelf.id = shelf_id
        mock_shelf.aisle_number = 1
        mock_shelf.shelf_number = 1

        mock_level = MagicMock()
        mock_level.id = level_id
        mock_level.shelf_id = shelf_id
        mock_level.level_number = 1

        mock_loc = MagicMock()
        mock_loc.id = loc_id
        mock_loc.level_id = level_id
        mock_loc.position_number = 1
        mock_loc.nfc_tag = None

        mock_task = MagicMock()
        mock_task.origin_location_id = None
        mock_task.destination_location_id = loc_id
        mock_task.type = MagicMock(value="entrada")

        db.execute.side_effect = [
            _make_result_single(mock_wh),    # get warehouse
            _make_result_list(mock_shelf),   # get shelves
            _make_result_list(mock_level),   # get levels
            _make_result_list(mock_loc),     # get locations
            _make_result_list(),             # get inventory
            _make_result_list(mock_task),    # get active tasks
        ]

        result = await get_warehouse_full(warehouse_id=warehouse_id, db=db, current_user=user)

        assert str(loc_id) in result.active_task_locations
        assert result.active_task_info[str(loc_id)] == "entrada"


# ---------------------------------------------------------------------------
# expand_warehouse
# ---------------------------------------------------------------------------

class TestExpandWarehouse:

    async def test_not_found_raises_404(self):
        db = _mock_db()
        user = _mock_user()
        db.execute.return_value = _make_result_single(None)

        with pytest.raises(HTTPException) as exc_info:
            await expand_warehouse(
                warehouse_id=uuid.uuid4(),
                expand_data=WarehouseExpand(),
                db=db, current_user=user,
            )
        assert exc_info.value.status_code == 404

    async def test_extend_existing_aisle_adds_shelves_and_locations(self):
        """
        expand_warehouse with extend_aisles must append new shelves to an
        existing aisle and update the warehouse counters.
        """
        db = _mock_db()
        user = _mock_user()
        warehouse_id = uuid.uuid4()
        aisle_num = 1

        mock_wh = MagicMock(spec=Warehouse)
        mock_wh.id = warehouse_id
        mock_wh.num_shelves = 1
        mock_wh.total_locations = 6

        existing_shelf = MagicMock(spec=Shelf)
        existing_shelf.aisle_number = aisle_num
        existing_shelf.shelf_number = 1
        existing_shelf.is_double = False

        db.execute.side_effect = [
            _make_result_single(mock_wh),
            _make_result_list(existing_shelf),
        ]

        await expand_warehouse(
            warehouse_id=warehouse_id,
            expand_data=WarehouseExpand(
                extend_aisles=[
                    ExtendAisleConfig(
                        aisle_number=aisle_num,
                        new_shelves=[ShelfConfig(num_levels=2, num_locations=3)],
                    )
                ]
            ),
            db=db, current_user=user,
        )

        assert mock_wh.num_shelves == 2      # 1 existing + 1 new
        assert mock_wh.total_locations == 12 # 6 existing + 2*3 new
        db.commit.assert_awaited_once()

    async def test_extend_unknown_aisle_raises_400(self):
        """extend_aisles referencing an aisle that does not exist returns 400."""
        db = _mock_db()
        user = _mock_user()
        warehouse_id = uuid.uuid4()

        mock_wh = MagicMock(spec=Warehouse)
        existing_shelf = MagicMock(spec=Shelf)
        existing_shelf.aisle_number = 1
        existing_shelf.shelf_number = 1
        existing_shelf.is_double = False

        db.execute.side_effect = [
            _make_result_single(mock_wh),
            _make_result_list(existing_shelf),
        ]

        with pytest.raises(HTTPException) as exc_info:
            await expand_warehouse(
                warehouse_id=warehouse_id,
                expand_data=WarehouseExpand(
                    extend_aisles=[
                        ExtendAisleConfig(aisle_number=99, new_shelves=[ShelfConfig(num_levels=1, num_locations=1)])
                    ]
                ),
                db=db, current_user=user,
            )
        assert exc_info.value.status_code == 400
        assert "99" in exc_info.value.detail

    async def test_add_new_aisles_updates_warehouse(self):
        """expand_warehouse with new_aisles adds a fresh aisle."""
        db = _mock_db()
        user = _mock_user()
        warehouse_id = uuid.uuid4()

        mock_wh = MagicMock(spec=Warehouse)
        mock_wh.num_shelves = 1
        mock_wh.total_locations = 4

        existing_shelf = MagicMock(spec=Shelf)
        existing_shelf.aisle_number = 1
        existing_shelf.shelf_number = 1
        existing_shelf.is_double = False

        db.execute.side_effect = [
            _make_result_single(mock_wh),
            _make_result_list(existing_shelf),
        ]

        await expand_warehouse(
            warehouse_id=warehouse_id,
            expand_data=WarehouseExpand(
                new_aisles=[AisleConfig(shelves=[ShelfConfig(num_levels=1, num_locations=2)])]
            ),
            db=db, current_user=user,
        )

        assert mock_wh.num_shelves == 2
        assert mock_wh.total_locations == 6  # 4 + 2
        db.commit.assert_awaited_once()

    async def test_add_new_double_aisle_generates_back_shelf(self):
        """new_aisles with is_double=True must generate a back-aisle row."""
        db = _mock_db()
        user = _mock_user()
        warehouse_id = uuid.uuid4()

        mock_wh = MagicMock(spec=Warehouse)
        mock_wh.num_shelves = 0
        mock_wh.total_locations = 0

        existing_shelf = MagicMock(spec=Shelf)
        existing_shelf.aisle_number = 1
        existing_shelf.shelf_number = 1
        existing_shelf.is_double = False

        db.execute.side_effect = [
            _make_result_single(mock_wh),
            _make_result_list(existing_shelf),
        ]

        await expand_warehouse(
            warehouse_id=warehouse_id,
            expand_data=WarehouseExpand(
                new_aisles=[AisleConfig(shelves=[ShelfConfig(num_levels=1, num_locations=2, is_double=True)])]
            ),
            db=db, current_user=user,
        )

        # 2 shelf rows (front + back) × 1 level × 2 locations = 4
        assert mock_wh.num_shelves == 2
        assert mock_wh.total_locations == 4

    async def test_extend_double_aisle_adds_back_shelf_too(self):
        """
        Extending a double aisle must also add a mirrored shelf to the back aisle
        (the is_double branch inside extend_aisles).
        """
        db = _mock_db()
        user = _mock_user()
        warehouse_id = uuid.uuid4()

        mock_wh = MagicMock(spec=Warehouse)
        mock_wh.num_shelves = 2
        mock_wh.total_locations = 8

        front_shelf = MagicMock(spec=Shelf)
        front_shelf.aisle_number = 1
        front_shelf.shelf_number = 1
        front_shelf.is_double = True

        back_shelf = MagicMock(spec=Shelf)
        back_shelf.aisle_number = 2
        back_shelf.shelf_number = 1
        back_shelf.is_double = False

        db.execute.side_effect = [
            _make_result_single(mock_wh),
            _make_result_list(front_shelf, back_shelf),
        ]

        await expand_warehouse(
            warehouse_id=warehouse_id,
            expand_data=WarehouseExpand(
                extend_aisles=[
                    ExtendAisleConfig(
                        aisle_number=1,
                        new_shelves=[ShelfConfig(num_levels=1, num_locations=2)],
                    )
                ]
            ),
            db=db, current_user=user,
        )

        # front shelf + mirrored back shelf = 2 new, each 1×2 = 2 locs → +4
        assert mock_wh.num_shelves == 4
        assert mock_wh.total_locations == 12


# ---------------------------------------------------------------------------
# update_warehouse
# ---------------------------------------------------------------------------

class TestUpdateWarehouse:

    async def test_found_renames_warehouse_and_returns_it(self):
        """update_warehouse updates the name attribute and commits the change."""
        db = _mock_db()
        user = _mock_user()
        wh_id = uuid.uuid4()

        mock_wh = MagicMock(spec=Warehouse)
        mock_wh.id = wh_id
        mock_wh.name = "Old Name"
        db.execute.return_value = _make_result_single(mock_wh)

        update_data = WarehouseNameUpdate(name="New Name")
        result = await update_warehouse(
            warehouse_id=wh_id, warehouse_data=update_data, db=db, current_user=user
        )

        assert mock_wh.name == "New Name"
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()
        assert result is mock_wh

    async def test_not_found_raises_404(self):
        """update_warehouse raises HTTP 404 when the warehouse is not found."""
        db = _mock_db()
        user = _mock_user()
        db.execute.return_value = _make_result_single(None)

        with pytest.raises(HTTPException) as exc_info:
            await update_warehouse(
                warehouse_id=uuid.uuid4(),
                warehouse_data=WarehouseNameUpdate(name="X"),
                db=db,
                current_user=user,
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_warehouse
# ---------------------------------------------------------------------------

class TestDeleteWarehouse:

    async def test_found_deletes_warehouse(self):
        """delete_warehouse calls db.delete on the warehouse and commits."""
        db = _mock_db()
        user = _mock_user()
        mock_wh = MagicMock(spec=Warehouse)
        db.execute.return_value = _make_result_single(mock_wh)

        await delete_warehouse(warehouse_id=uuid.uuid4(), db=db, current_user=user)

        db.delete.assert_awaited_once_with(mock_wh)
        db.commit.assert_awaited_once()

    async def test_not_found_raises_404(self):
        """delete_warehouse raises HTTP 404 when the warehouse is not found."""
        db = _mock_db()
        user = _mock_user()
        db.execute.return_value = _make_result_single(None)

        with pytest.raises(HTTPException) as exc_info:
            await delete_warehouse(warehouse_id=uuid.uuid4(), db=db, current_user=user)

        assert exc_info.value.status_code == 404
