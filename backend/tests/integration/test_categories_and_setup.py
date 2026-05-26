"""
Integration tests for endpoints with low or zero existing coverage:

  GET  /categories         — list company categories
  POST /categories         — create a category (admin)
  POST /locations/{id}/inventory — seed inventory into an empty location

These endpoints were not exercised before; covering them removes the
remaining gap in `app/api/categories.py` and the inventory-setup branch in
`app/api/locations.py`.

Pattern: Arrange → Act → Assert
"""

import uuid
from unittest.mock import patch, AsyncMock

import pytest

from app.models.models import Category, InventoryItem, Box


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class TestCategories:

    async def test_list_returns_company_categories(
        self, client, base_data, admin_token, db_session
    ):
        company = base_data["company"]
        db_session.add_all([
            Category(id=uuid.uuid4(), company_id=company.id, name="Aceites", color="#111111"),
            Category(id=uuid.uuid4(), company_id=company.id, name="Bebidas", color="#222222"),
        ])
        await db_session.commit()

        response = await client.get("/categories", headers=_auth(admin_token))
        assert response.status_code == 200
        names = [c["name"] for c in response.json()]
        assert names == ["Aceites", "Bebidas"]  # ordered by name

    async def test_worker_can_list_categories(self, client, base_data, worker_token):
        """Workers also read /categories — endpoint depends on get_current_user."""
        response = await client.get("/categories", headers=_auth(worker_token))
        assert response.status_code == 200
        assert response.json() == []

    async def test_admin_creates_category(self, client, base_data, admin_token):
        response = await client.post(
            "/categories",
            headers=_auth(admin_token),
            json={"name": "Frutería", "color": "#33aa55"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Frutería"
        assert body["color"] == "#33aa55"

    async def test_worker_forbidden_from_creating_category(
        self, client, base_data, worker_token
    ):
        response = await client.post(
            "/categories",
            headers=_auth(worker_token),
            json={"name": "Nope"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Location inventory setup
# ---------------------------------------------------------------------------

class TestLocationInventorySetup:

    async def test_setup_with_quantity_one_creates_loose_item(
        self, client, base_data, admin_token, db_session
    ):
        """quantity=1 → InventoryItem.product_id set, no Box created."""
        loc = base_data["location1"]
        product = base_data["product1"]

        with patch("app.api.locations.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            response = await client.post(
                f"/locations/{loc.id}/inventory",
                headers=_auth(admin_token),
                json={"product_id": str(product.id), "quantity": 1},
            )

        assert response.status_code == 201
        # Confirm in DB: item points directly to the product, no box
        from sqlalchemy import select
        item = (await db_session.execute(
            select(InventoryItem).where(InventoryItem.location_id == loc.id)
        )).scalar_one()
        assert item.product_id == product.id
        assert item.box_id is None

    async def test_setup_with_quantity_greater_than_one_creates_box(
        self, client, base_data, admin_token, db_session
    ):
        """quantity>1 → a Box is created and the InventoryItem points to it."""
        loc = base_data["location1"]
        product = base_data["product1"]

        with patch("app.api.locations.websocket_service") as mock_ws:
            mock_ws.broadcast_movement_created = AsyncMock()
            response = await client.post(
                f"/locations/{loc.id}/inventory",
                headers=_auth(admin_token),
                json={"product_id": str(product.id), "quantity": 5},
            )

        assert response.status_code == 201
        from sqlalchemy import select
        item = (await db_session.execute(
            select(InventoryItem).where(InventoryItem.location_id == loc.id)
        )).scalar_one()
        assert item.product_id is None
        assert item.box_id is not None
        box = (await db_session.execute(select(Box).where(Box.id == item.box_id))).scalar_one()
        assert box.current_quantity == 5

    async def test_setup_on_unknown_location_returns_404(
        self, client, base_data, admin_token
    ):
        product = base_data["product1"]
        response = await client.post(
            f"/locations/{uuid.uuid4()}/inventory",
            headers=_auth(admin_token),
            json={"product_id": str(product.id), "quantity": 1},
        )
        assert response.status_code == 404

    async def test_setup_with_unknown_product_returns_404(
        self, client, base_data, admin_token
    ):
        loc = base_data["location1"]
        response = await client.post(
            f"/locations/{loc.id}/inventory",
            headers=_auth(admin_token),
            json={"product_id": str(uuid.uuid4()), "quantity": 1},
        )
        assert response.status_code == 404

    async def test_setup_on_occupied_location_returns_409(
        self, client, base_data, admin_token, db_session
    ):
        loc = base_data["location1"]
        product = base_data["product1"]
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=loc.id,
            product_id=product.id,
            quantity=1,
        ))
        await db_session.commit()

        response = await client.post(
            f"/locations/{loc.id}/inventory",
            headers=_auth(admin_token),
            json={"product_id": str(product.id), "quantity": 1},
        )
        assert response.status_code == 409

    async def test_worker_forbidden_from_setup(self, client, base_data, worker_token):
        loc = base_data["location1"]
        product = base_data["product1"]
        response = await client.post(
            f"/locations/{loc.id}/inventory",
            headers=_auth(worker_token),
            json={"product_id": str(product.id), "quantity": 1},
        )
        assert response.status_code == 403
