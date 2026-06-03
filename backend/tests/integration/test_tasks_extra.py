"""
Integration tests for the task-management endpoints not exercised by the
existing unit suite.

Endpoints covered:
  GET    /tasks                — list company tasks (admin)
  GET    /tasks/{id}           — fetch a single task
  GET    /tasks/user/{id}      — tasks assigned to a user
  GET    /tasks/recommendation — recommend a worker for the next task
  GET    /tasks/stats          — per-worker and global statistics
  DELETE /tasks/{id}           — delete a pending task; reject in-progress
  POST   /tasks                — create task with traslado / salida / occupied
                                  destination / active conflict guards

Every test runs against the in-memory SQLite DB so we exercise the real
SQLAlchemy queries; mocking would hide the JOINs and subqueries that make
tasks.py the largest module in the project.

Pattern: Arrange → Act → Assert
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

import pytest

from app.models.models import (
    Task, TaskType, TaskStatus, InventoryItem, Movement, MovementType, Product,
)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

class TestListTasks:

    async def test_admin_lists_company_tasks(self, client, base_data, admin_token, db_session):
        """GET /tasks returns every task in the admin's company."""
        admin = base_data["admin"]
        worker = base_data["worker"]
        db_session.add(Task(
            id=uuid.uuid4(),
            company_id=admin.company_id,
            created_by=admin.id,
            assigned_to=worker.id,
            type=TaskType.entrada,
            destination_location_id=base_data["location1"].id,
        ))
        await db_session.commit()

        response = await client.get("/tasks", headers=_auth(admin_token))

        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_worker_forbidden_from_listing(self, client, base_data, worker_token):
        """GET /tasks requires admin; a worker token returns 403."""
        response = await client.get("/tasks", headers=_auth(worker_token))
        assert response.status_code == 403

    async def test_get_task_by_id_404_when_missing(self, client, base_data, admin_token):
        """GET /tasks/{id} returns 404 when no task with that id exists in the company."""
        response = await client.get(f"/tasks/{uuid.uuid4()}", headers=_auth(admin_token))
        assert response.status_code == 404

    async def test_get_task_by_id_returns_task(self, client, base_data, admin_token, db_session):
        admin = base_data["admin"]
        worker = base_data["worker"]
        task_id = uuid.uuid4()
        db_session.add(Task(
            id=task_id,
            company_id=admin.company_id,
            created_by=admin.id,
            assigned_to=worker.id,
            type=TaskType.entrada,
            destination_location_id=base_data["location2"].id,
        ))
        await db_session.commit()

        response = await client.get(f"/tasks/{task_id}", headers=_auth(admin_token))
        assert response.status_code == 200
        assert response.json()["id"] == str(task_id)

    async def test_get_tasks_by_user_returns_only_workers_tasks(
        self, client, base_data, worker_token, db_session
    ):
        """GET /tasks/user/{id} returns the tasks assigned to that user."""
        admin = base_data["admin"]
        worker = base_data["worker"]
        db_session.add_all([
            Task(
                id=uuid.uuid4(),
                company_id=admin.company_id,
                created_by=admin.id,
                assigned_to=worker.id,
                type=TaskType.entrada,
                destination_location_id=base_data["location1"].id,
            ),
            Task(
                id=uuid.uuid4(),
                company_id=admin.company_id,
                created_by=admin.id,
                assigned_to=admin.id,  # assigned to admin → must be excluded
                type=TaskType.entrada,
                destination_location_id=base_data["location2"].id,
            ),
        ])
        await db_session.commit()

        response = await client.get(f"/tasks/user/{worker.id}", headers=_auth(worker_token))
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["assigned_to"] == str(worker.id)


# ---------------------------------------------------------------------------
# Stats and recommendation
# ---------------------------------------------------------------------------

class TestRecommendation:

    async def test_no_workers_returns_empty_list(self, client, base_data, admin_token, db_session):
        """When no active workers exist in the company, the recommendation list is empty."""
        worker = base_data["worker"]
        worker.is_active = False
        db_session.add(worker)
        await db_session.commit()

        response = await client.get("/tasks/recommendation", headers=_auth(admin_token))
        assert response.status_code == 200
        assert response.json() == []

    async def test_recommends_least_loaded_worker(
        self, client, base_data, admin_token, db_session
    ):
        """
        With tasks distributed unevenly, the worker with the lowest score
        (fewer pending today) is marked is_recommended=True.
        """
        admin = base_data["admin"]
        worker = base_data["worker"]
        # Assign the worker 2 pending tasks today
        for _ in range(2):
            db_session.add(Task(
                id=uuid.uuid4(),
                company_id=admin.company_id,
                created_by=admin.id,
                assigned_to=worker.id,
                type=TaskType.entrada,
                status=TaskStatus.pendiente,
                destination_location_id=uuid.uuid4(),
            ))
        await db_session.commit()

        response = await client.get("/tasks/recommendation", headers=_auth(admin_token))
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        rec = body[0]
        assert rec["user_id"] == str(worker.id)
        assert rec["pending_today"] == 2
        assert rec["is_recommended"] is True


class TestStats:

    async def test_stats_with_no_workers(self, client, base_data, admin_token, db_session):
        """/tasks/stats returns zero global metrics when no workers are active."""
        worker = base_data["worker"]
        worker.is_active = False
        db_session.add(worker)
        await db_session.commit()

        response = await client.get("/tasks/stats", headers=_auth(admin_token))
        assert response.status_code == 200
        body = response.json()
        assert body["workers"] == []
        assert body["global_total_movements"] == 0
        assert body["global_completion_rate"] == 0.0

    async def test_stats_counts_completed_and_pending(
        self, client, base_data, admin_token, db_session
    ):
        """Stats: completion_rate, completed_this_week and busiest_day are populated."""
        admin = base_data["admin"]
        worker = base_data["worker"]
        # 1 completed + 1 pending → 50% completion
        completed_id = uuid.uuid4()
        db_session.add_all([
            Task(
                id=completed_id,
                company_id=admin.company_id,
                created_by=admin.id,
                assigned_to=worker.id,
                type=TaskType.entrada,
                status=TaskStatus.completada,
                destination_location_id=uuid.uuid4(),
                completed_at=datetime.utcnow(),
            ),
            Task(
                id=uuid.uuid4(),
                company_id=admin.company_id,
                created_by=admin.id,
                assigned_to=worker.id,
                type=TaskType.entrada,
                status=TaskStatus.pendiente,
                destination_location_id=uuid.uuid4(),
            ),
        ])
        # One movement today → busiest_day populated
        db_session.add(Movement(
            id=uuid.uuid4(),
            company_id=admin.company_id,
            task_id=completed_id,
            performed_by=worker.id,
            type=MovementType.entrada,
            destination_location_id=base_data["location1"].id,
        ))
        await db_session.commit()

        response = await client.get("/tasks/stats", headers=_auth(admin_token))
        assert response.status_code == 200
        body = response.json()
        assert len(body["workers"]) == 1
        w = body["workers"][0]
        assert w["total_assigned"] == 2
        assert w["total_completed"] == 1
        assert w["total_pending"] == 1
        assert w["completion_rate"] == 50.0
        assert body["global_total_movements"] == 1
        assert body["busiest_day"] is not None
        assert body["most_active_worker"] == "Worker Test"


# ---------------------------------------------------------------------------
# create_task: extra branches
# ---------------------------------------------------------------------------

class TestCreateTaskBranches:

    async def test_entrada_without_destination_returns_400(
        self, client, base_data, admin_token
    ):
        worker = base_data["worker"]
        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={"assigned_to": str(worker.id), "type": "entrada"},
        )
        assert response.status_code == 400
        assert "destino" in response.json()["detail"].lower()

    async def test_salida_without_origin_returns_400(self, client, base_data, admin_token):
        worker = base_data["worker"]
        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={"assigned_to": str(worker.id), "type": "salida"},
        )
        assert response.status_code == 400
        assert "origen" in response.json()["detail"].lower()

    async def test_traslado_without_locations_returns_400(
        self, client, base_data, admin_token
    ):
        worker = base_data["worker"]
        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={"assigned_to": str(worker.id), "type": "traslado"},
        )
        assert response.status_code == 400

    async def test_salida_requires_product_id(self, client, base_data, admin_token):
        worker = base_data["worker"]
        loc = base_data["location1"]
        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={
                "assigned_to": str(worker.id),
                "type": "salida",
                "origin_location_id": str(loc.id),
            },
        )
        assert response.status_code == 400
        assert "producto" in response.json()["detail"].lower()

    async def test_salida_fails_when_origin_empty(self, client, base_data, admin_token):
        worker = base_data["worker"]
        product = base_data["product1"]
        loc = base_data["location1"]  # empty
        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={
                "assigned_to": str(worker.id),
                "type": "salida",
                "origin_location_id": str(loc.id),
                "product_id": str(product.id),
            },
        )
        assert response.status_code == 400
        assert "origen" in response.json()["detail"].lower()

    async def test_entrada_with_inventory_setup_succeeds(
        self, client, base_data, admin_token, db_session
    ):
        """create_task entrada on an empty destination commits and emits ws event."""
        worker = base_data["worker"]
        loc = base_data["location2"]
        product = base_data["product1"]

        with patch("app.api.tasks.websocket_service") as mock_ws:
            mock_ws.broadcast_task_assigned = AsyncMock()
            response = await client.post(
                "/tasks",
                headers=_auth(admin_token),
                json={
                    "assigned_to": str(worker.id),
                    "type": "entrada",
                    "destination_location_id": str(loc.id),
                    "product_id": str(product.id),
                    "quantity": 1,
                },
            )

        assert response.status_code == 201
        assert response.json()["status"] == "pendiente"
        mock_ws.broadcast_task_assigned.assert_awaited_once()

    async def test_creating_second_task_for_same_destination_returns_400(
        self, client, base_data, admin_token, db_session
    ):
        """Two active tasks cannot share a destination location."""
        admin = base_data["admin"]
        worker = base_data["worker"]
        loc = base_data["location2"]
        product = base_data["product1"]
        db_session.add(Task(
            id=uuid.uuid4(),
            company_id=admin.company_id,
            created_by=admin.id,
            assigned_to=worker.id,
            type=TaskType.entrada,
            status=TaskStatus.pendiente,
            destination_location_id=loc.id,
            product_id=product.id,
        ))
        await db_session.commit()

        response = await client.post(
            "/tasks",
            headers=_auth(admin_token),
            json={
                "assigned_to": str(worker.id),
                "type": "entrada",
                "destination_location_id": str(loc.id),
                "product_id": str(product.id),
            },
        )
        assert response.status_code == 400
        assert "tarea activa" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# delete_task
# ---------------------------------------------------------------------------

class TestDeleteTask:

    async def test_delete_pending_task_succeeds(
        self, client, base_data, admin_token, db_session
    ):
        admin = base_data["admin"]
        worker = base_data["worker"]
        task_id = uuid.uuid4()
        db_session.add(Task(
            id=task_id,
            company_id=admin.company_id,
            created_by=admin.id,
            assigned_to=worker.id,
            type=TaskType.entrada,
            status=TaskStatus.pendiente,
            destination_location_id=base_data["location1"].id,
        ))
        await db_session.commit()

        response = await client.delete(f"/tasks/{task_id}", headers=_auth(admin_token))
        assert response.status_code == 204

    async def test_delete_unknown_task_returns_404(self, client, base_data, admin_token):
        response = await client.delete(f"/tasks/{uuid.uuid4()}", headers=_auth(admin_token))
        assert response.status_code == 404

    async def test_delete_in_progress_task_returns_400(
        self, client, base_data, admin_token, db_session
    ):
        admin = base_data["admin"]
        worker = base_data["worker"]
        task_id = uuid.uuid4()
        db_session.add(Task(
            id=task_id,
            company_id=admin.company_id,
            created_by=admin.id,
            assigned_to=worker.id,
            type=TaskType.entrada,
            status=TaskStatus.en_curso,
            destination_location_id=base_data["location1"].id,
        ))
        await db_session.commit()

        response = await client.delete(f"/tasks/{task_id}", headers=_auth(admin_token))
        assert response.status_code == 400
        assert "curso" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# update_task_status: real DB path
# ---------------------------------------------------------------------------

class TestUpdateTaskStatusHttp:

    async def test_completing_task_sets_completed_at_and_broadcasts(
        self, client, base_data, worker_token, db_session
    ):
        admin = base_data["admin"]
        worker = base_data["worker"]
        task_id = uuid.uuid4()
        db_session.add(Task(
            id=task_id,
            company_id=admin.company_id,
            created_by=admin.id,
            assigned_to=worker.id,
            type=TaskType.entrada,
            status=TaskStatus.en_curso,
            destination_location_id=base_data["location1"].id,
        ))
        await db_session.commit()

        with patch("app.api.tasks.websocket_service") as mock_ws:
            mock_ws.broadcast_task_status_changed = AsyncMock()
            response = await client.put(
                f"/tasks/{task_id}/status",
                headers=_auth(worker_token),
                json={"status": "completada"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completada"
        assert body["completed_at"] is not None
        mock_ws.broadcast_task_status_changed.assert_awaited_once()
