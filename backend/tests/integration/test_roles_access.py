"""
Integration tests for role-based access control (RBAC).

RNF-05: the system enforces two roles:
  - admin : can create warehouses, products, users and tasks;
            can read all movements.
  - worker: can register movements and read their own tasks;
            cannot perform admin-only operations.

Each test makes a single HTTP request with the appropriate token and
asserts the HTTP status code returned by the production FastAPI app.
The in-memory SQLite DB (from conftest.py) is used for all tests.

Pattern: Arrange → Act → Assert
"""

import uuid
import pytest

from app.models.models import InventoryItem


class TestWorkerRestrictions:

    async def test_worker_cannot_create_warehouse_returns_403(
        self, client, base_data, worker_token
    ):
        """
        POST /warehouses with a worker token must return HTTP 403.
        Creating warehouses is an admin-only operation (get_current_admin dependency).
        """
        # Arrange
        payload = {
            "name": "Forbidden Warehouse",
            "aisles": [{"shelves": [{"num_levels": 1, "num_locations": 2}]}],
        }

        # Act
        response = await client.post(
            "/warehouses",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=payload,
        )

        # Assert
        assert response.status_code == 403

    async def test_worker_cannot_create_product_returns_403(
        self, client, base_data, worker_token
    ):
        """
        POST /products with a worker token must return HTTP 403.
        Product management is restricted to admins.
        """
        # Arrange
        payload = {"name": "Forbidden Product"}

        # Act
        response = await client.post(
            "/products",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=payload,
        )

        # Assert
        assert response.status_code == 403

    async def test_worker_cannot_create_task_returns_403(
        self, client, base_data, worker_token
    ):
        """
        POST /tasks with a worker token must return HTTP 403.
        Task creation is an admin-only operation.
        """
        # Arrange
        payload = {
            "assigned_to": str(base_data["worker"].id),
            "type": "entrada",
            "destination_location_id": str(base_data["location1"].id),
        }

        # Act
        response = await client.post(
            "/tasks",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=payload,
        )

        # Assert
        assert response.status_code == 403

    async def test_worker_cannot_list_all_tasks_returns_403(
        self, client, base_data, worker_token
    ):
        """
        GET /tasks (all company tasks) with a worker token must return HTTP 403.
        Workers can only see their own tasks via /tasks/user/{user_id}.
        """
        # Act
        response = await client.get(
            "/tasks", headers={"Authorization": f"Bearer {worker_token}"}
        )

        # Assert
        assert response.status_code == 403


class TestAdminPrivileges:

    async def test_admin_can_create_warehouse_returns_201(
        self, client, base_data, admin_token
    ):
        """
        POST /warehouses with a valid admin token must return HTTP 201.
        The response body must contain the warehouse name and a UUID id.
        """
        # Arrange
        payload = {
            "name": "Admin Warehouse",
            "aisles": [
                {"shelves": [{"num_levels": 2, "num_locations": 3}]},
            ],
        }

        # Act
        response = await client.post(
            "/warehouses",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=payload,
        )

        # Assert
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Admin Warehouse"
        assert "id" in body

    async def test_admin_can_list_warehouses_returns_200(
        self, client, base_data, admin_token
    ):
        """
        GET /warehouses with an admin token must return HTTP 200 and a list
        containing at least the warehouse created in base_data.
        """
        # Act
        response = await client.get(
            "/warehouses", headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) >= 1


class TestWorkerPermissions:

    async def test_worker_can_register_movement_returns_201(
        self, client, base_data, worker_token
    ):
        """
        POST /movements with a worker token and valid payload must return HTTP 201.
        Workers are explicitly allowed to register movements (the create_movement
        handler uses get_current_user, not get_current_admin).
        """
        # Arrange: location1 is empty (base_data contains no InventoryItems)
        payload = {
            "task_id": str(uuid.uuid4()),
            "type": "entrada",
            "product_id": str(base_data["product1"].id),
            "destination_location_id": str(base_data["location1"].id),
            "quantity": 1,
        }

        # Act
        response = await client.post(
            "/movements",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=payload,
        )

        # Assert
        assert response.status_code == 201

    async def test_worker_can_get_own_tasks_returns_200(
        self, client, base_data, worker_token
    ):
        """
        GET /tasks/user/{worker_id} with a worker token must return HTTP 200.
        Workers can query their own task list (possibly empty).
        The endpoint uses get_current_user (not get_current_admin), so workers
        are permitted access.
        """
        # Arrange
        worker_id = str(base_data["worker"].id)

        # Act
        response = await client.get(
            f"/tasks/user/{worker_id}",
            headers={"Authorization": f"Bearer {worker_token}"},
        )

        # Assert
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_worker_can_read_inventory_returns_200(
        self, client, base_data, worker_token
    ):
        """
        GET /inventory with a worker token must return HTTP 200.
        Inventory is readable by all authenticated users (get_current_user).
        """
        # Act
        response = await client.get(
            "/inventory",
            headers={"Authorization": f"Bearer {worker_token}"},
        )

        # Assert
        assert response.status_code == 200

    async def test_worker_can_update_task_status_returns_200(
        self, client, base_data, admin_token, worker_token, db_session
    ):
        """
        PUT /tasks/{task_id}/status with a worker token must return HTTP 200.
        Status updates (e.g. marking a task as 'en_curso') are allowed for
        all authenticated users — workers update their assigned tasks as they
        execute them.
        """
        # Arrange: create a task via admin, then update it via worker
        from app.models.models import Task, TaskType, TaskStatus

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

        # Act
        response = await client.put(
            f"/tasks/{task.id}/status",
            headers={"Authorization": f"Bearer {worker_token}"},
            json={"status": "en_curso"},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "en_curso"


class TestUnauthenticatedAccess:

    async def test_warehouses_without_token_returns_401(self, client, base_data):
        """
        GET /warehouses without an Authorization header must return HTTP 401.
        RNF-04: no endpoint (except /auth/login) is publicly accessible.
        """
        response = await client.get("/warehouses")
        assert response.status_code == 401

    async def test_inventory_without_token_returns_401(self, client, base_data):
        """
        GET /inventory without an Authorization header must return HTTP 401.
        """
        response = await client.get("/inventory")
        assert response.status_code == 401

    async def test_tasks_without_token_returns_401(self, client, base_data):
        """
        GET /tasks without an Authorization header must return HTTP 401.
        """
        response = await client.get("/tasks")
        assert response.status_code == 401
