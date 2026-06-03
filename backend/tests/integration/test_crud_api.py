"""
Additional integration tests covering CRUD endpoints that were not yet tested,
added to push branch coverage above the 75% threshold.

Endpoints covered in this file:
  GET/POST/PUT/DELETE  /products
  GET                  /products/barcode/{barcode}
  GET                  /warehouses/{id}
  GET                  /warehouses/{id}/full
  PUT/DELETE           /warehouses/{id}
  GET/POST/DELETE      /tasks  (extra scenarios)
  GET                  /inventory/summary
  GET                  /inventory/{item_id}

Pattern: Arrange → Act → Assert
"""

import uuid
import pytest

from app.models.models import InventoryItem, Task, TaskType, TaskStatus, Category, Warehouse


# ---------------------------------------------------------------------------
# Products CRUD
# ---------------------------------------------------------------------------

class TestProductsCrud:

    async def test_admin_can_list_products_returns_200(
        self, client, base_data, admin_token
    ):
        """GET /products with admin token must return 200 and include base_data products."""
        response = await client.get(
            "/products", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        names = [p["name"] for p in body]
        assert "Product Alpha" in names
        assert "Product Beta" in names

    async def test_admin_can_create_product_returns_201(
        self, client, base_data, admin_token
    ):
        """POST /products with admin token must return 201 and the new product."""
        response = await client.post(
            "/products",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "New Product", "barcode": "BARNEW", "description": "desc"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "New Product"
        assert body["barcode"] == "BARNEW"
        assert "id" in body

    async def test_admin_can_get_product_by_id_returns_200(
        self, client, base_data, admin_token
    ):
        """GET /products/{id} returns the product when it exists."""
        pid = str(base_data["product1"].id)
        response = await client.get(
            f"/products/{pid}", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Product Alpha"

    async def test_get_product_by_id_not_found_returns_404(
        self, client, base_data, admin_token
    ):
        """GET /products/{id} for a non-existent product must return 404."""
        response = await client.get(
            f"/products/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_admin_can_get_product_by_barcode(
        self, client, base_data, admin_token
    ):
        """GET /products/barcode/{barcode} returns the product matching the barcode."""
        response = await client.get(
            "/products/barcode/BAR001",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["barcode"] == "BAR001"

    async def test_get_product_by_unknown_barcode_returns_404(
        self, client, base_data, admin_token
    ):
        """GET /products/barcode/{barcode} for an unknown barcode must return 404."""
        response = await client.get(
            "/products/barcode/NOTEXIST",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_admin_can_update_product_returns_200(
        self, client, base_data, admin_token
    ):
        """PUT /products/{id} must update product fields and return the updated product."""
        pid = str(base_data["product1"].id)
        response = await client.put(
            f"/products/{pid}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Product Alpha Updated", "barcode": "BAR001-NEW"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Product Alpha Updated"

    async def test_admin_can_delete_product_returns_204(
        self, client, base_data, admin_token
    ):
        """DELETE /products/{id} must remove the product and return 204."""
        pid = str(base_data["product2"].id)
        response = await client.delete(
            f"/products/{pid}", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 204

        # Verify it is gone
        get_response = await client.get(
            f"/products/{pid}", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 404

    async def test_delete_nonexistent_product_returns_404(
        self, client, base_data, admin_token
    ):
        """DELETE /products/{id} for an unknown product must return 404."""
        response = await client.delete(
            f"/products/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Warehouses CRUD
# ---------------------------------------------------------------------------

class TestWarehousesCrud:

    async def test_admin_can_get_warehouse_by_id_returns_200(
        self, client, base_data, admin_token
    ):
        """GET /warehouses/{id} returns the warehouse details."""
        wid = str(base_data["warehouse"].id)
        response = await client.get(
            f"/warehouses/{wid}", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Test Warehouse"

    async def test_get_warehouse_by_unknown_id_returns_404(
        self, client, base_data, admin_token
    ):
        """GET /warehouses/{id} for a non-existent warehouse must return 404."""
        response = await client.get(
            f"/warehouses/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_admin_can_get_warehouse_full_returns_hierarchy(
        self, client, base_data, admin_token
    ):
        """
        GET /warehouses/{id}/full must return the complete shelf/level/location
        hierarchy for the digital twin.  The response must include 1 shelf,
        1 level and 2 locations matching the base_data structure.
        """
        wid = str(base_data["warehouse"].id)
        response = await client.get(
            f"/warehouses/{wid}/full",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == wid
        assert len(body["shelves"]) == 1
        shelf = body["shelves"][0]
        assert len(shelf["levels"]) == 1
        assert len(shelf["levels"][0]["locations"]) == 2

    async def test_get_warehouse_full_with_inventory_shows_items(
        self, client, base_data, admin_token, db_session
    ):
        """
        GET /warehouses/{id}/full must include inventory data when a location is
        occupied.  The digital twin uses this to colour occupied shelves.
        """
        # Arrange: put an item in location1
        item = InventoryItem(
            id=uuid.uuid4(),
            location_id=base_data["location1"].id,
            product_id=base_data["product1"].id,
            quantity=5,
        )
        db_session.add(item)
        await db_session.commit()

        wid = str(base_data["warehouse"].id)
        response = await client.get(
            f"/warehouses/{wid}/full",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        locations = response.json()["shelves"][0]["levels"][0]["locations"]
        occupied = [loc for loc in locations if loc["inventory"] is not None]
        assert len(occupied) == 1
        assert occupied[0]["inventory"]["quantity"] == 5

    async def test_admin_can_update_warehouse_name_returns_200(
        self, client, base_data, admin_token
    ):
        """PUT /warehouses/{id} must rename the warehouse and return the updated record."""
        wid = str(base_data["warehouse"].id)
        response = await client.put(
            f"/warehouses/{wid}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Renamed Warehouse"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Renamed Warehouse"

    async def test_admin_can_delete_warehouse_returns_204(
        self, client, base_data, admin_token
    ):
        """DELETE /warehouses/{id} must remove the warehouse and return 204."""
        create_resp = await client.post(
            "/warehouses",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "To Delete", "aisles": [{"shelves": [{"num_levels": 1, "num_locations": 1}]}]},
        )
        assert create_resp.status_code == 201
        wid = create_resp.json()["id"]

        delete_resp = await client.delete(
            f"/warehouses/{wid}", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert delete_resp.status_code == 204

    async def test_create_warehouse_with_double_shelf(
        self, client, base_data, admin_token
    ):
        """POST /warehouses with is_double=True must generate a mirrored back aisle."""
        response = await client.post(
            "/warehouses",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Double Warehouse",
                "aisles": [{"shelves": [{"num_levels": 2, "num_locations": 3, "is_double": True}]}],
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["num_shelves"] == 2          # front + back
        assert body["total_locations"] == 12    # 2 sides × 2 levels × 3 locs

    async def test_expand_warehouse_with_new_aisle(
        self, client, base_data, admin_token
    ):
        """POST /warehouses/{id}/expand with new_aisles adds shelves and updates counters."""
        # Create a fresh warehouse to expand
        create_resp = await client.post(
            "/warehouses",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Expandable", "aisles": [{"shelves": [{"num_levels": 1, "num_locations": 2}]}]},
        )
        assert create_resp.status_code == 201
        wid = create_resp.json()["id"]
        original_locs = create_resp.json()["total_locations"]  # 2

        response = await client.post(
            f"/warehouses/{wid}/expand",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"new_aisles": [{"shelves": [{"num_levels": 1, "num_locations": 3}]}], "extend_aisles": []},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total_locations"] == original_locs + 3
        assert body["num_shelves"] == 2

    async def test_expand_warehouse_extend_existing_aisle(
        self, client, base_data, admin_token
    ):
        """POST /warehouses/{id}/expand with extend_aisles adds to an existing aisle."""
        create_resp = await client.post(
            "/warehouses",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Extendable", "aisles": [{"shelves": [{"num_levels": 1, "num_locations": 2}]}]},
        )
        wid = create_resp.json()["id"]

        response = await client.post(
            f"/warehouses/{wid}/expand",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "new_aisles": [],
                "extend_aisles": [{"aisle_number": 1, "new_shelves": [{"num_levels": 1, "num_locations": 2}]}],
            },
        )
        assert response.status_code == 200
        assert response.json()["total_locations"] == 4  # 2 + 2

    async def test_expand_unknown_warehouse_returns_404(
        self, client, base_data, admin_token
    ):
        response = await client.post(
            f"/warehouses/{uuid.uuid4()}/expand",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"new_aisles": [], "extend_aisles": []},
        )
        assert response.status_code == 404

    async def test_expand_unknown_aisle_returns_400(
        self, client, base_data, admin_token
    ):
        create_resp = await client.post(
            "/warehouses",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "W", "aisles": [{"shelves": [{"num_levels": 1, "num_locations": 1}]}]},
        )
        wid = create_resp.json()["id"]

        response = await client.post(
            f"/warehouses/{wid}/expand",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "new_aisles": [],
                "extend_aisles": [{"aisle_number": 99, "new_shelves": [{"num_levels": 1, "num_locations": 1}]}],
            },
        )
        assert response.status_code == 400

    async def test_warehouse_full_with_categorized_product(
        self, client, base_data, admin_token, db_session
    ):
        """GET /warehouses/{id}/full must populate category fields when the product has one."""
        company = base_data["company"]
        cat = Category(id=uuid.uuid4(), company_id=company.id, name="Electrónica", color="#0000FF")
        db_session.add(cat)
        product = base_data["product1"]
        product.category_id = cat.id
        db_session.add(product)
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=base_data["location1"].id,
            product_id=product.id,
            quantity=2,
        ))
        await db_session.commit()

        wid = str(base_data["warehouse"].id)
        response = await client.get(f"/warehouses/{wid}/full", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200

        locations = response.json()["shelves"][0]["levels"][0]["locations"]
        occupied = [l for l in locations if l["inventory"] is not None]
        assert len(occupied) == 1
        assert occupied[0]["inventory"]["product_category"] == "Electrónica"
        assert occupied[0]["inventory"]["product_category_color"] == "#0000FF"

    async def test_warehouse_full_active_task_with_origin_location(
        self, client, base_data, admin_token, db_session
    ):
        """GET /warehouses/{id}/full includes origin_location_id in active_task_info."""
        admin = base_data["admin"]
        worker = base_data["worker"]
        origin = base_data["location1"]
        product = base_data["product1"]

        db_session.add(InventoryItem(
            id=uuid.uuid4(), location_id=origin.id, product_id=product.id, quantity=3,
        ))
        db_session.add(Task(
            id=uuid.uuid4(),
            company_id=admin.company_id,
            created_by=admin.id,
            assigned_to=worker.id,
            type=TaskType.salida,
            status=TaskStatus.pendiente,
            origin_location_id=origin.id,
            product_id=product.id,
            quantity=1,
        ))
        await db_session.commit()

        wid = str(base_data["warehouse"].id)
        response = await client.get(f"/warehouses/{wid}/full", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        body = response.json()
        assert str(origin.id) in body["active_task_locations"]
        assert body["active_task_info"][str(origin.id)] == "salida"


# ---------------------------------------------------------------------------
# Tasks: additional scenarios
# ---------------------------------------------------------------------------

class TestTasksAdditional:

    async def test_admin_can_list_all_tasks_returns_200(
        self, client, base_data, admin_token
    ):
        """GET /tasks with admin token must return 200 and a list."""
        response = await client.get(
            "/tasks", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_admin_can_get_task_by_id(
        self, client, base_data, admin_token, db_session
    ):
        """GET /tasks/{id} with admin token returns the specific task."""
        task = Task(
            id=uuid.uuid4(),
            company_id=base_data["company"].id,
            created_by=base_data["admin"].id,
            assigned_to=base_data["worker"].id,
            type=TaskType.entrada,
            status=TaskStatus.pendiente,
            destination_location_id=base_data["location1"].id,
        )
        db_session.add(task)
        await db_session.commit()

        response = await client.get(
            f"/tasks/{task.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(task.id)

    async def test_get_task_not_found_returns_404(
        self, client, base_data, admin_token
    ):
        """GET /tasks/{id} for a non-existent task must return 404."""
        response = await client.get(
            f"/tasks/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_admin_can_create_entrada_task_returns_201(
        self, client, base_data, admin_token
    ):
        """
        POST /tasks with type=entrada must return 201 and status=pendiente.
        The destination location must be free and the assigned user in the company.
        """
        response = await client.post(
            "/tasks",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "assigned_to": str(base_data["worker"].id),
                "type": "entrada",
                "product_id": str(base_data["product1"].id),
                "destination_location_id": str(base_data["location1"].id),
                "quantity": 2,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pendiente"
        assert body["type"] == "entrada"

    async def test_admin_can_delete_task_returns_204(
        self, client, base_data, admin_token, db_session
    ):
        """DELETE /tasks/{id} for a pendiente task must return 204."""
        task = Task(
            id=uuid.uuid4(),
            company_id=base_data["company"].id,
            created_by=base_data["admin"].id,
            assigned_to=base_data["worker"].id,
            type=TaskType.entrada,
            status=TaskStatus.pendiente,
        )
        db_session.add(task)
        await db_session.commit()

        response = await client.delete(
            f"/tasks/{task.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

    async def test_delete_in_progress_task_returns_400(
        self, client, base_data, admin_token, db_session
    ):
        """DELETE /tasks/{id} for an en_curso task must return 400 (cannot interrupt)."""
        task = Task(
            id=uuid.uuid4(),
            company_id=base_data["company"].id,
            created_by=base_data["admin"].id,
            assigned_to=base_data["worker"].id,
            type=TaskType.entrada,
            status=TaskStatus.en_curso,
        )
        db_session.add(task)
        await db_session.commit()

        response = await client.delete(
            f"/tasks/{task.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400

    async def test_create_task_requires_origin_for_salida(
        self, client, base_data, admin_token, db_session
    ):
        """
        POST /tasks with type=salida and no origin_location_id must return 400.
        A salida needs an origin from which to pick up goods.
        """
        response = await client.post(
            "/tasks",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "assigned_to": str(base_data["worker"].id),
                "type": "salida",
                "product_id": str(base_data["product1"].id),
                # origin_location_id intentionally omitted
            },
        )
        assert response.status_code == 400

    async def test_create_traslado_task_with_occupied_origin_returns_201(
        self, client, base_data, admin_token, db_session
    ):
        """
        POST /tasks with type=traslado requires the origin to have the product.
        The happy path: origin has the product and destination is free → 201.
        """
        # Arrange: put product1 at location1
        item = InventoryItem(
            id=uuid.uuid4(),
            location_id=base_data["location1"].id,
            product_id=base_data["product1"].id,
            quantity=5,
        )
        db_session.add(item)
        await db_session.commit()

        response = await client.post(
            "/tasks",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "assigned_to": str(base_data["worker"].id),
                "type": "traslado",
                "product_id": str(base_data["product1"].id),
                "origin_location_id": str(base_data["location1"].id),
                "destination_location_id": str(base_data["location2"].id),
            },
        )
        assert response.status_code == 201
        assert response.json()["type"] == "traslado"


# ---------------------------------------------------------------------------
# Inventory: additional endpoints
# ---------------------------------------------------------------------------

class TestInventoryAdditional:

    async def test_get_inventory_summary_returns_200(
        self, client, base_data, admin_token
    ):
        """GET /inventory/summary must return 200 and a list of product stock summaries."""
        response = await client.get(
            "/inventory/summary",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_inventory_summary_reflects_stock(
        self, client, base_data, worker_token, db_session
    ):
        """
        After creating an InventoryItem, /inventory/summary must report at least
        1 unit of that product in stock.
        """
        # Arrange: add item for product1 at location1
        item = InventoryItem(
            id=uuid.uuid4(),
            location_id=base_data["location1"].id,
            product_id=base_data["product1"].id,
            quantity=7,
        )
        db_session.add(item)
        await db_session.commit()

        response = await client.get(
            "/inventory/summary",
            headers={"Authorization": f"Bearer {worker_token}"},
        )
        assert response.status_code == 200
        summaries = response.json()
        product1_row = next(
            (s for s in summaries if s["product_id"] == str(base_data["product1"].id)),
            None,
        )
        assert product1_row is not None
        assert product1_row["total_units"] >= 7

    async def test_get_inventory_item_by_id_returns_200(
        self, client, base_data, worker_token, db_session
    ):
        """GET /inventory/{item_id} must return the specific InventoryItem."""
        item = InventoryItem(
            id=uuid.uuid4(),
            location_id=base_data["location1"].id,
            product_id=base_data["product1"].id,
            quantity=3,
        )
        db_session.add(item)
        await db_session.commit()

        response = await client.get(
            f"/inventory/{item.id}",
            headers={"Authorization": f"Bearer {worker_token}"},
        )
        assert response.status_code == 200
        assert response.json()["quantity"] == 3

    async def test_get_inventory_item_not_found_returns_404(
        self, client, base_data, worker_token
    ):
        """GET /inventory/{item_id} for a non-existent item must return 404."""
        response = await client.get(
            f"/inventory/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {worker_token}"},
        )
        assert response.status_code == 404
