"""
Unit tests for products, boxes, shelves, and locations handler functions.

Handlers are called directly with mocked AsyncSession and current_user objects.
This ensures coverage.py traces the function bodies via direct coroutine calls
rather than going through httpx's ASGITransport.

Pattern: Arrange → Act → Assert
"""

import uuid
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.exc import IntegrityError

import pytest
from fastapi import HTTPException

from app.api.products import (
    get_products,
    create_product,
    get_product_by_barcode,
    get_product,
    update_product,
    delete_product,
)
from app.api.boxes import (
    get_boxes,
    create_box,
    get_box,
    update_box,
)
from app.api.shelves import (
    get_shelves,
    get_shelf,
    get_levels,
    get_level,
)
from app.api.locations import (
    get_locations,
    get_location,
    get_location_by_nfc,
    update_location_nfc,
)
from app.models.models import Product, Box, Shelf, Level, Location
from app.schemas.schemas import ProductCreate, BoxCreate, LocationNFCUpdate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _mock_user(company_id=None):
    user = MagicMock()
    user.company_id = company_id or uuid.uuid4()
    return user


def _single(item):
    r = MagicMock()
    r.scalar_one_or_none.return_value = item
    return r


def _list_result(*items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = list(items)
    return r


# ===========================================================================
# Products
# ===========================================================================

class TestGetProducts:

    async def test_returns_all_company_products(self):
        """get_products fetches all products for the current user's company."""
        db = _mock_db()
        user = _mock_user()
        mock_product = MagicMock(spec=Product)
        db.execute.return_value = _list_result(mock_product)

        result = await get_products(db=db, current_user=user)

        assert len(result) == 1

    async def test_returns_empty_list_when_no_products(self):
        db = _mock_db()
        db.execute.return_value = _list_result()

        result = await get_products(db=db, current_user=_mock_user())

        assert result == []


class TestCreateProduct:

    async def test_creates_and_returns_product(self):
        """
        create_product persists a new Product and returns it. After commit the
        handler re-queries the product via _get_product_with_category which uses
        scalar_one(), so we mock that result with the created product.
        """
        db = _mock_db()
        user = _mock_user()
        created = MagicMock(spec=Product)
        created.name = "Widget"
        created.barcode = "BAR-001"
        db.execute.return_value = MagicMock(**{"scalar_one.return_value": created})
        product_data = ProductCreate(name="Widget", barcode="BAR-001", description="desc")

        result = await create_product(product_data=product_data, db=db, current_user=user)

        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        assert result.name == "Widget"
        assert result.barcode == "BAR-001"


class TestGetProductByBarcode:

    async def test_found_returns_product(self):
        """get_product_by_barcode returns the product when the barcode exists."""
        db = _mock_db()
        user = _mock_user()
        mock_product = MagicMock(spec=Product)
        db.execute.return_value = _single(mock_product)

        result = await get_product_by_barcode(barcode="BAR-001", db=db, current_user=user)

        assert result is mock_product

    async def test_not_found_raises_404(self):
        """get_product_by_barcode raises HTTP 404 for an unknown barcode."""
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_product_by_barcode(barcode="NOTEXIST", db=db, current_user=_mock_user())

        assert exc_info.value.status_code == 404


class TestGetProduct:

    async def test_found_returns_product(self):
        db = _mock_db()
        mock_product = MagicMock(spec=Product)
        db.execute.return_value = _single(mock_product)

        result = await get_product(product_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert result is mock_product

    async def test_not_found_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_product(product_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert exc_info.value.status_code == 404


class TestUpdateProduct:

    async def test_updates_product_and_returns_it(self):
        """
        update_product modifies product fields, commits, and returns the product
        re-fetched via _get_product_with_category (a second execute() call).
        """
        db = _mock_db()
        user = _mock_user()
        mock_product = MagicMock(spec=Product)
        reloaded = MagicMock(spec=Product)
        reloaded.name = "Updated"

        db.execute.side_effect = [
            _single(mock_product),                                          # initial fetch
            MagicMock(**{"scalar_one.return_value": reloaded}),             # reload after commit
        ]

        product_data = ProductCreate(name="Updated", barcode="NEW-001", description="d", type="t")
        result = await update_product(
            product_id=uuid.uuid4(), product_data=product_data, db=db, current_user=user
        )

        assert mock_product.name == "Updated"
        db.commit.assert_awaited_once()
        assert result is reloaded

    async def test_not_found_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await update_product(
                product_id=uuid.uuid4(),
                product_data=ProductCreate(name="X"),
                db=db,
                current_user=_mock_user(),
            )

        assert exc_info.value.status_code == 404


class TestDeleteProduct:

    async def test_found_deletes_product(self):
        """delete_product calls db.delete and commits."""
        db = _mock_db()
        mock_product = MagicMock(spec=Product)
        db.execute.return_value = _single(mock_product)

        await delete_product(product_id=uuid.uuid4(), db=db, current_user=_mock_user())

        db.delete.assert_awaited_once_with(mock_product)
        db.commit.assert_awaited_once()

    async def test_not_found_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await delete_product(product_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert exc_info.value.status_code == 404


# ===========================================================================
# Boxes
# ===========================================================================

class TestGetBoxes:

    async def test_returns_all_company_boxes(self):
        db = _mock_db()
        mock_box = MagicMock(spec=Box)
        db.execute.return_value = _list_result(mock_box)

        result = await get_boxes(db=db, current_user=_mock_user())

        assert len(result) == 1


class TestCreateBox:

    async def test_creates_and_returns_box(self):
        """create_box persists a Box and returns it."""
        db = _mock_db()
        user = _mock_user()
        box_data = BoxCreate(product_id=uuid.uuid4(), current_quantity=5, max_capacity=10)

        result = await create_box(box_data=box_data, db=db, current_user=user)

        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        assert result.current_quantity == 5
        assert result.max_capacity == 10


class TestGetBox:

    async def test_found_returns_box(self):
        db = _mock_db()
        mock_box = MagicMock(spec=Box)
        db.execute.return_value = _single(mock_box)

        result = await get_box(box_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert result is mock_box

    async def test_not_found_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_box(box_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert exc_info.value.status_code == 404


class TestUpdateBox:

    async def test_updates_and_returns_box(self):
        db = _mock_db()
        mock_box = MagicMock(spec=Box)
        db.execute.return_value = _single(mock_box)

        box_data = BoxCreate(product_id=uuid.uuid4(), current_quantity=8, max_capacity=20)
        result = await update_box(box_id=uuid.uuid4(), box_data=box_data, db=db, current_user=_mock_user())

        assert mock_box.current_quantity == 8
        assert mock_box.max_capacity == 20
        db.commit.assert_awaited_once()
        assert result is mock_box

    async def test_not_found_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await update_box(
                box_id=uuid.uuid4(),
                box_data=BoxCreate(product_id=uuid.uuid4(), current_quantity=1, max_capacity=5),
                db=db,
                current_user=_mock_user(),
            )

        assert exc_info.value.status_code == 404


# ===========================================================================
# Shelves
# ===========================================================================

class TestGetShelves:

    async def test_unknown_warehouse_raises_404(self):
        """get_shelves raises HTTP 404 when the warehouse is not in the company."""
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_shelves(warehouse_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert exc_info.value.status_code == 404

    async def test_known_warehouse_returns_shelves(self):
        """get_shelves returns the shelves for a valid warehouse."""
        db = _mock_db()
        mock_wh = MagicMock()
        mock_shelf = MagicMock(spec=Shelf)
        db.execute.side_effect = [
            _single(mock_wh),         # warehouse check
            _list_result(mock_shelf), # shelves query
        ]

        result = await get_shelves(warehouse_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert len(result) == 1


class TestGetShelf:

    async def test_found_returns_shelf(self):
        db = _mock_db()
        mock_shelf = MagicMock(spec=Shelf)
        db.execute.return_value = _single(mock_shelf)

        result = await get_shelf(shelf_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert result is mock_shelf

    async def test_not_found_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_shelf(shelf_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert exc_info.value.status_code == 404


class TestGetLevels:

    async def test_returns_levels_for_shelf(self):
        db = _mock_db()
        mock_level = MagicMock(spec=Level)
        db.execute.return_value = _list_result(mock_level)

        result = await get_levels(shelf_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert len(result) == 1


class TestGetLevel:

    async def test_found_returns_level(self):
        db = _mock_db()
        mock_level = MagicMock(spec=Level)
        db.execute.return_value = _single(mock_level)

        result = await get_level(level_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert result is mock_level

    async def test_not_found_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_level(level_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert exc_info.value.status_code == 404


# ===========================================================================
# Locations
# ===========================================================================

class TestGetLocations:

    async def test_returns_locations_for_level(self):
        db = _mock_db()
        mock_loc = MagicMock(spec=Location)
        db.execute.return_value = _list_result(mock_loc)

        result = await get_locations(level_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert len(result) == 1


class TestGetLocation:

    async def test_found_returns_location(self):
        db = _mock_db()
        mock_loc = MagicMock(spec=Location)
        db.execute.return_value = _single(mock_loc)

        result = await get_location(location_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert result is mock_loc

    async def test_not_found_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_location(location_id=uuid.uuid4(), db=db, current_user=_mock_user())

        assert exc_info.value.status_code == 404


class TestGetLocationByNfc:

    async def test_found_returns_location(self):
        db = _mock_db()
        mock_loc = MagicMock(spec=Location)
        db.execute.return_value = _single(mock_loc)

        result = await get_location_by_nfc(nfc_tag="NFC-001", db=db, current_user=_mock_user())

        assert result is mock_loc

    async def test_unknown_tag_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_location_by_nfc(nfc_tag="UNKNOWN", db=db, current_user=_mock_user())

        assert exc_info.value.status_code == 404


class TestUpdateLocationNfc:

    async def test_assigns_nfc_tag_to_location(self):
        """update_location_nfc sets nfc_tag, commits, and returns the location."""
        db = _mock_db()
        mock_loc = MagicMock(spec=Location)
        mock_loc.nfc_tag = None
        db.execute.return_value = _single(mock_loc)

        nfc_data = LocationNFCUpdate(nfc_tag="NEW-NFC-001")
        result = await update_location_nfc(
            location_id=uuid.uuid4(), nfc_data=nfc_data, db=db, current_user=_mock_user()
        )

        assert mock_loc.nfc_tag == "NEW-NFC-001"
        db.commit.assert_awaited_once()
        assert result is mock_loc

    async def test_not_found_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)

        with pytest.raises(HTTPException) as exc_info:
            await update_location_nfc(
                location_id=uuid.uuid4(),
                nfc_data=LocationNFCUpdate(nfc_tag="X"),
                db=db,
                current_user=_mock_user(),
            )

        assert exc_info.value.status_code == 404

    async def test_duplicate_nfc_tag_raises_409(self):
        """update_location_nfc raises HTTP 409 when the NFC tag is already in use."""
        db = _mock_db()
        mock_loc = MagicMock(spec=Location)
        db.execute.return_value = _single(mock_loc)
        db.commit.side_effect = IntegrityError("UNIQUE constraint", None, None)

        with pytest.raises(HTTPException) as exc_info:
            await update_location_nfc(
                location_id=uuid.uuid4(),
                nfc_data=LocationNFCUpdate(nfc_tag="DUPLICATE"),
                db=db,
                current_user=_mock_user(),
            )

        db.rollback.assert_awaited_once()
        assert exc_info.value.status_code == 409
