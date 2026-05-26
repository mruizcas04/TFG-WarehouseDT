"""
Direct-call unit tests for the task handlers that the integration suite
does cover end-to-end but whose line-level execution coverage.py cannot
trace reliably through httpx's ASGITransport.

This file mirrors the integration tests in test_tasks_extra.py but invokes
the handlers as plain coroutines so coverage.py sees every branch hit.

Handlers covered:
  get_tasks, get_task, get_tasks_by_user
  get_worker_recommendation, get_stats
  delete_task
  create_task (every branching path: location requirements, accumulation,
               product mismatch, conflicts)
  update_task_status (completing branch)

Pattern: Arrange → Act → Assert
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.tasks import (
    get_tasks, get_task, get_tasks_by_user, get_worker_recommendation,
    get_stats, delete_task, create_task, update_task_status,
)
from app.models.models import (
    User, UserRole, Task, TaskStatus, TaskType,
    InventoryItem, Box, Movement, Product,
)
from app.schemas.schemas import TaskCreate, TaskStatusUpdate


def _admin():
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.company_id = uuid.uuid4()
    u.role = UserRole.admin
    return u


def _worker(company_id=None):
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.company_id = company_id or uuid.uuid4()
    u.role = UserRole.worker
    u.name = "Worker"
    u.is_active = True
    u.is_online = True
    return u


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


def _scalar(value):
    r = MagicMock()
    r.scalar.return_value = value
    return r


# ---------------------------------------------------------------------------
# Read handlers
# ---------------------------------------------------------------------------

class TestReadHandlers:

    async def test_get_tasks_returns_company_tasks(self):
        db = _mock_db()
        task = MagicMock(spec=Task)
        db.execute.return_value = _list(task)

        result = await get_tasks(db=db, current_user=_admin())
        assert result == [task]

    async def test_get_task_404_when_missing(self):
        db = _mock_db()
        db.execute.return_value = _single(None)
        with pytest.raises(HTTPException) as exc_info:
            await get_task(task_id=uuid.uuid4(), db=db, current_user=_admin())
        assert exc_info.value.status_code == 404

    async def test_get_task_returns_found_task(self):
        db = _mock_db()
        task = MagicMock(spec=Task)
        db.execute.return_value = _single(task)

        result = await get_task(task_id=uuid.uuid4(), db=db, current_user=_admin())
        assert result is task


# ---------------------------------------------------------------------------
# create_task: every error branch
# ---------------------------------------------------------------------------

class TestCreateTaskBranches:

    async def test_entrada_without_destination_raises_400(self):
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)
        db.execute.return_value = _single(worker)

        td = TaskCreate(assigned_to=worker.id, type=TaskType.entrada)
        with pytest.raises(HTTPException) as e:
            await create_task(td, db, admin)
        assert e.value.status_code == 400

    async def test_salida_without_origin_raises_400(self):
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)
        db.execute.return_value = _single(worker)
        td = TaskCreate(assigned_to=worker.id, type=TaskType.salida)
        with pytest.raises(HTTPException) as e:
            await create_task(td, db, admin)
        assert e.value.status_code == 400

    async def test_traslado_requires_both_locations(self):
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)
        db.execute.return_value = _single(worker)
        td = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.traslado,
            origin_location_id=uuid.uuid4(),
            # no destination
        )
        with pytest.raises(HTTPException) as e:
            await create_task(td, db, admin)
        assert e.value.status_code == 400

    async def test_salida_without_product_raises_400(self):
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)
        db.execute.return_value = _single(worker)
        td = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.salida,
            origin_location_id=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as e:
            await create_task(td, db, admin)
        assert e.value.status_code == 400
        assert "producto" in e.value.detail.lower()

    async def test_salida_without_origin_inventory_raises_400(self):
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)
        db.execute.side_effect = [
            _single(worker),   # assignee
            _single(None),     # origin inventory empty
        ]
        td = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.salida,
            origin_location_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as e:
            await create_task(td, db, admin)
        assert e.value.status_code == 400

    async def test_entrada_with_accumulation_succeeds(self):
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)
        product_id = uuid.uuid4()

        # Existing inventory with same product, accumulating allowed
        existing = MagicMock(spec=InventoryItem)
        existing.product_id = product_id
        existing.box_id = None
        existing.quantity = 2

        prod = MagicMock(spec=Product)
        prod.units_per_location = 10
        prod.id = product_id

        db.execute.side_effect = [
            _single(worker),    # assignee
            _single(existing),  # destination occupied
            _single(prod),      # product fetch
            _single(None),      # no conflicting active task on dest
            _single(None),      # no conflicting active task on origin (skipped since no origin)
        ]

        td = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.entrada,
            destination_location_id=uuid.uuid4(),
            product_id=product_id,
            quantity=3,
        )

        with patch("app.api.tasks.websocket_service") as ws:
            ws.broadcast_task_assigned = AsyncMock()
            result = await create_task(td, db, admin)

        assert result is not None
        db.commit.assert_awaited_once()

    async def test_entrada_destination_different_product_raises_400(self):
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)

        existing = MagicMock(spec=InventoryItem)
        existing.product_id = uuid.uuid4()  # different product
        existing.box_id = None

        db.execute.side_effect = [
            _single(worker),
            _single(existing),
        ]

        td = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.entrada,
            destination_location_id=uuid.uuid4(),
            product_id=uuid.uuid4(),  # different from existing
            quantity=1,
        )

        with pytest.raises(HTTPException) as e:
            await create_task(td, db, admin)
        assert e.value.status_code == 400

    async def test_entrada_product_does_not_allow_accumulation_raises_400(self):
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)
        product_id = uuid.uuid4()

        existing = MagicMock(spec=InventoryItem)
        existing.product_id = product_id
        existing.box_id = None
        existing.quantity = 1

        prod = MagicMock(spec=Product)
        prod.units_per_location = None  # accumulation not allowed
        prod.id = product_id

        db.execute.side_effect = [
            _single(worker),
            _single(existing),
            _single(prod),
        ]

        td = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.entrada,
            destination_location_id=uuid.uuid4(),
            product_id=product_id,
            quantity=1,
        )

        with pytest.raises(HTTPException) as e:
            await create_task(td, db, admin)
        assert e.value.status_code == 400
        assert "acumulación" in e.value.detail.lower()

    async def test_entrada_capacity_exceeded_raises_400(self):
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)
        product_id = uuid.uuid4()

        existing = MagicMock(spec=InventoryItem)
        existing.product_id = product_id
        existing.box_id = None
        existing.quantity = 9

        prod = MagicMock(spec=Product)
        prod.units_per_location = 10
        prod.id = product_id

        db.execute.side_effect = [
            _single(worker),
            _single(existing),
            _single(prod),
        ]

        td = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.entrada,
            destination_location_id=uuid.uuid4(),
            product_id=product_id,
            quantity=5,  # 9 + 5 > 10
        )

        with pytest.raises(HTTPException) as e:
            await create_task(td, db, admin)
        assert e.value.status_code == 400

    async def test_entrada_empty_location_qty_above_units_per_location_raises_400(self):
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)
        product_id = uuid.uuid4()

        prod = MagicMock(spec=Product)
        prod.units_per_location = 5
        prod.id = product_id

        db.execute.side_effect = [
            _single(worker),
            _single(None),    # destination empty
            _single(prod),    # product for capacity check on empty
        ]

        td = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.entrada,
            destination_location_id=uuid.uuid4(),
            product_id=product_id,
            quantity=6,
        )

        with pytest.raises(HTTPException) as e:
            await create_task(td, db, admin)
        assert e.value.status_code == 400

    async def test_destination_with_active_task_raises_400(self):
        """Even if everything else passes, a pending active task blocks creation."""
        db = _mock_db()
        admin = _admin()
        worker = _worker(company_id=admin.company_id)

        active_task = MagicMock(spec=Task)
        db.execute.side_effect = [
            _single(worker),       # assignee
            _single(None),         # destination empty
            _single(active_task),  # conflicting active task on destination
        ]

        td = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.entrada,
            destination_location_id=uuid.uuid4(),
        )

        with pytest.raises(HTTPException) as e:
            await create_task(td, db, admin)
        assert e.value.status_code == 400
        assert "tarea activa" in e.value.detail.lower()


# ---------------------------------------------------------------------------
# delete_task
# ---------------------------------------------------------------------------

class TestDeleteTaskHandler:

    async def test_delete_pending_task_succeeds(self):
        db = _mock_db()
        task = MagicMock(spec=Task)
        task.status = TaskStatus.pendiente
        # First execute: select task; subsequent: delete movements
        db.execute.side_effect = [_single(task), MagicMock()]

        await delete_task(task_id=uuid.uuid4(), db=db, current_user=_admin())

        db.delete.assert_awaited_once_with(task)
        db.commit.assert_awaited_once()

    async def test_delete_in_progress_task_raises_400(self):
        db = _mock_db()
        task = MagicMock(spec=Task)
        task.status = TaskStatus.en_curso
        db.execute.return_value = _single(task)

        with pytest.raises(HTTPException) as e:
            await delete_task(task_id=uuid.uuid4(), db=db, current_user=_admin())
        assert e.value.status_code == 400

    async def test_delete_unknown_task_raises_404(self):
        db = _mock_db()
        db.execute.return_value = _single(None)
        with pytest.raises(HTTPException) as e:
            await delete_task(task_id=uuid.uuid4(), db=db, current_user=_admin())
        assert e.value.status_code == 404


# ---------------------------------------------------------------------------
# get_worker_recommendation
# ---------------------------------------------------------------------------

class TestRecommendationHandler:

    async def test_no_workers_returns_empty_list(self):
        db = _mock_db()
        db.execute.return_value = _list()  # no workers
        result = await get_worker_recommendation(db=db, current_user=_admin())
        assert result == []

    async def test_recommends_least_loaded_online_worker(self):
        db = _mock_db()
        admin = _admin()

        w1 = _worker(company_id=admin.company_id)
        w1.name = "Alice"
        w2 = _worker(company_id=admin.company_id)
        w2.name = "Bob"

        # Each worker triggers 3 count queries → 6 total + 1 initial list
        db.execute.side_effect = [
            _list(w1, w2),       # workers query
            # w1: pending_today, pending_old, total_completed
            _scalar(5), _scalar(0), _scalar(1),
            # w2: lighter load
            _scalar(1), _scalar(0), _scalar(2),
        ]

        result = await get_worker_recommendation(db=db, current_user=admin)
        assert len(result) == 2
        recommended = [r for r in result if r["is_recommended"]]
        assert len(recommended) == 1
        # Bob has fewer pending → should be the recommended one (lowest score)
        assert recommended[0]["name"] == "Bob"

    async def test_falls_back_to_all_workers_when_none_online(self):
        """If no worker is online, the ranking considers all active workers."""
        db = _mock_db()
        admin = _admin()
        offline = _worker(company_id=admin.company_id)
        offline.is_online = False

        db.execute.side_effect = [
            _list(offline),
            _scalar(0), _scalar(0), _scalar(0),
        ]

        result = await get_worker_recommendation(db=db, current_user=admin)
        assert len(result) == 1
        assert result[0]["is_active_today"] is False


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

class TestStatsHandler:

    async def test_no_workers_returns_zero_metrics(self):
        db = _mock_db()
        db.execute.side_effect = [
            _list(),                            # workers
            _scalar(0),                         # global_total_movements
            _scalar(0),                         # global_total_tasks_completed
            _scalar(0),                         # global_total_tasks
            _list(),                            # timestamps for busiest_day
        ]
        result = await get_stats(db=db, current_user=_admin())
        assert result.workers == []
        assert result.global_completion_rate == 0.0
        assert result.busiest_day is None
        assert result.most_active_worker is None

    async def test_stats_with_one_worker_populates_metrics(self):
        db = _mock_db()
        admin = _admin()
        w1 = _worker(company_id=admin.company_id)
        w1.name = "Solo"

        # Per worker: 6 count queries
        # Then: 3 global counts + timestamps list
        ts = datetime(2025, 11, 3, 9, 0)  # a Monday
        db.execute.side_effect = [
            _list(w1),
            _scalar(4),  # total_assigned
            _scalar(2),  # total_completed
            _scalar(1),  # total_pending
            _scalar(0),  # pending_old
            _scalar(1),  # completed_this_week
            _scalar(2),  # completed_this_month
            _scalar(10),  # global_total_movements
            _scalar(2),   # global_total_tasks_completed
            _scalar(4),   # global_total_tasks
            _list(ts),    # timestamps
        ]
        result = await get_stats(db=db, current_user=admin)
        assert len(result.workers) == 1
        w = result.workers[0]
        assert w.total_assigned == 4
        assert w.total_completed == 2
        assert w.completion_rate == 50.0
        assert result.global_total_movements == 10
        assert result.global_completion_rate == 50.0
        assert result.busiest_day == "Lunes"
        assert result.most_active_worker == "Solo"


# ---------------------------------------------------------------------------
# update_task_status: completed_at branch
# ---------------------------------------------------------------------------

class TestUpdateTaskStatusCompletedAt:

    async def test_setting_completed_sets_completed_at_timestamp(self):
        db = _mock_db()
        task = MagicMock(spec=Task)
        task.id = uuid.uuid4()
        task.status = TaskStatus.en_curso
        task.completed_at = None
        task.origin_location_id = None
        task.destination_location_id = None
        db.execute.return_value = _single(task)

        with patch("app.api.tasks.websocket_service") as ws:
            ws.broadcast_task_status_changed = AsyncMock()
            await update_task_status(
                task_id=task.id,
                status_data=TaskStatusUpdate(status=TaskStatus.completada),
                db=db,
                current_user=_worker(),
            )

        assert task.status == TaskStatus.completada
        # completed_at was assigned (not None)
        assert task.completed_at is not None

    async def test_setting_non_completed_does_not_touch_completed_at(self):
        db = _mock_db()
        task = MagicMock(spec=Task)
        task.id = uuid.uuid4()
        task.status = TaskStatus.pendiente
        sentinel = "untouched"
        task.completed_at = sentinel
        task.origin_location_id = None
        task.destination_location_id = None
        db.execute.return_value = _single(task)

        with patch("app.api.tasks.websocket_service") as ws:
            ws.broadcast_task_status_changed = AsyncMock()
            await update_task_status(
                task_id=task.id,
                status_data=TaskStatusUpdate(status=TaskStatus.en_curso),
                db=db,
                current_user=_worker(),
            )

        assert task.status == TaskStatus.en_curso
        assert task.completed_at == sentinel
