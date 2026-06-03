"""
Integration tests for the inventory query endpoints and the product image
upload — the two areas that the rest of the suite leaves only partially
covered.

  GET  /inventory/summary       — per-product totals across loose items
                                  and boxes, including pending in/out
  GET  /inventory                — list company inventory items
  GET  /inventory/{id}           — fetch one inventory item
  POST /products/{id}/image      — upload product image (writes to uploads/products)

Pattern: Arrange → Act → Assert
"""

import io
import os
import uuid
from pathlib import Path

import pytest

from app.models.models import (
    InventoryItem, Task, TaskType, TaskStatus,
)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Inventory queries
# ---------------------------------------------------------------------------

class TestInventorySummary:

    async def test_empty_inventory_returns_one_row_per_product(
        self, client, base_data, admin_token
    ):
        """
        With no InventoryItems the summary still returns one row per product,
        with total_units=0 and no pending tasks.
        """
        response = await client.get("/inventory/summary", headers=_auth(admin_token))
        assert response.status_code == 200
        rows = response.json()
        # base_data has 2 products
        assert len(rows) == 2
        for r in rows:
            assert r["total_units"] == 0
            assert r["pending_in"] == 0
            assert r["pending_out"] == 0

    async def test_summary_counts_loose_units_and_pending(
        self, client, base_data, admin_token, db_session
    ):
        """A loose InventoryItem plus a pending entrada task feed the summary."""
        admin = base_data["admin"]
        worker = base_data["worker"]
        product = base_data["product1"]
        loc = base_data["location1"]

        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=loc.id,
            product_id=product.id,
            quantity=4,
        ))
        db_session.add(Task(
            id=uuid.uuid4(),
            company_id=admin.company_id,
            created_by=admin.id,
            assigned_to=worker.id,
            type=TaskType.entrada,
            status=TaskStatus.pendiente,
            product_id=product.id,
            destination_location_id=base_data["location2"].id,
            quantity=2,
        ))
        await db_session.commit()

        response = await client.get("/inventory/summary", headers=_auth(admin_token))
        assert response.status_code == 200
        rows = response.json()
        row = next(r for r in rows if r["product_id"] == str(product.id))
        assert row["total_units"] == 4
        assert row["locations_count"] == 1
        assert row["pending_in"] == 2


class TestInventoryReads:

    async def test_list_returns_company_items(
        self, client, base_data, admin_token, db_session
    ):
        product = base_data["product1"]
        loc = base_data["location1"]
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=loc.id,
            product_id=product.id,
            quantity=1,
        ))
        await db_session.commit()

        response = await client.get("/inventory", headers=_auth(admin_token))
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_get_unknown_item_returns_404(self, client, base_data, admin_token):
        response = await client.get(f"/inventory/{uuid.uuid4()}", headers=_auth(admin_token))
        assert response.status_code == 404

    async def test_get_known_item_returns_it(
        self, client, base_data, admin_token, db_session
    ):
        product = base_data["product1"]
        loc = base_data["location1"]
        item_id = uuid.uuid4()
        db_session.add(InventoryItem(
            id=item_id,
            location_id=loc.id,
            product_id=product.id,
            quantity=1,
        ))
        await db_session.commit()

        response = await client.get(f"/inventory/{item_id}", headers=_auth(admin_token))
        assert response.status_code == 200
        assert response.json()["id"] == str(item_id)


# ---------------------------------------------------------------------------
# Product image upload
# ---------------------------------------------------------------------------

class TestProductImageUpload:

    async def test_admin_uploads_jpeg_and_image_url_persists(
        self, client, base_data, admin_token, db_session, tmp_path, monkeypatch
    ):
        """
        Uploading a JPEG to /products/{id}/image saves the file under
        uploads/products and sets product.image_url. We redirect the upload
        dir to a tmp_path so the test doesn't leave artefacts behind.
        """
        product = base_data["product1"]
        target_dir = tmp_path / "products"
        monkeypatch.setattr("app.api.products.UPLOAD_DIR", str(target_dir))

        # Tiny valid-looking JPEG payload (header bytes are enough for our handler)
        fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 16

        response = await client.post(
            f"/products/{product.id}/image",
            headers=_auth(admin_token),
            files={"file": ("logo.jpg", io.BytesIO(fake_jpeg), "image/jpeg")},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["image_url"] is not None
        assert body["image_url"].endswith(".jpg")
        # File actually written
        assert os.path.exists(body["image_url"])

    async def test_unknown_product_returns_404(
        self, client, base_data, admin_token, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("app.api.products.UPLOAD_DIR", str(tmp_path / "p"))
        response = await client.post(
            f"/products/{uuid.uuid4()}/image",
            headers=_auth(admin_token),
            files={"file": ("logo.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")},
        )
        assert response.status_code == 404

    async def test_unsupported_content_type_returns_400(
        self, client, base_data, admin_token
    ):
        product = base_data["product1"]
        response = await client.post(
            f"/products/{product.id}/image",
            headers=_auth(admin_token),
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        assert response.status_code == 400

    async def test_worker_forbidden_from_uploading(
        self, client, base_data, worker_token
    ):
        product = base_data["product1"]
        response = await client.post(
            f"/products/{product.id}/image",
            headers=_auth(worker_token),
            files={"file": ("logo.jpg", io.BytesIO(b"\xff\xd8"), "image/jpeg")},
        )
        assert response.status_code == 403
