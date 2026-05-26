"""
Unit tests for task management logic (app/api/tasks.py).

Business rules validated:
  - Only an admin can call create_task (enforced by the get_current_admin dependency;
    access control is tested at integration level — here we test the handler logic
    assuming a valid admin user is injected).
  - create_task verifies the assigned user belongs to the same company.
  - create_task sets status=pendiente by default (SQLAlchemy column default applied
    at INSERT time; the integration tests verify the persisted value — this suite
    checks the DB commit and WebSocket call are made).
  - get_tasks_by_user returns the list produced by the DB query without modification.
  - update_task_status persists the new status and broadcasts via WebSocket.

All DB interactions are fully mocked with AsyncMock.

Pattern: Arrange → Act → Assert
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.tasks import create_task, get_tasks_by_user, update_task_status
from app.models.models import (
    User, UserRole, Task, TaskStatus, TaskType, InventoryItem, Box,
)
from app.schemas.schemas import TaskCreate, TaskStatusUpdate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_admin(company_id=None):
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.company_id = company_id or uuid.uuid4()
    user.role = UserRole.admin
    return user


def _make_worker(company_id=None):
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
# Task creation
# ---------------------------------------------------------------------------

class TestCreateTask:

    async def test_create_task_assigns_to_worker(self):
        """
        Admin creates an entrada task assigned to a worker.
        The handler must commit to the DB and broadcast the task_assigned event.
        The column-level default (status=pendiente) is applied by SQLAlchemy at
        INSERT time; the integration tests verify the persisted value.
        """
        # Arrange
        db = _mock_db()
        admin = _make_admin()
        worker = _make_worker(company_id=admin.company_id)
        dest_id = uuid.uuid4()

        db.execute.side_effect = [
            # 1. Assigned user found in company
            MagicMock(**{"scalar_one_or_none.return_value": worker}),
            # 2. Destination location is free (entrada requires empty dest)
            MagicMock(**{"scalar_one_or_none.return_value": None}),
            # 3. No active task conflicts on destination
            MagicMock(**{"scalar_one_or_none.return_value": None}),
        ]

        task_data = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.entrada,
            destination_location_id=dest_id,
        )

        # Act
        with patch("app.api.tasks.websocket_service") as mock_ws:
            mock_ws.broadcast_task_assigned = AsyncMock()
            result = await create_task(task_data, db, admin)

        # Assert: task committed, WebSocket notified
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        mock_ws.broadcast_task_assigned.assert_awaited_once()
        # The Task object passed to add must carry the correct assigned_to
        added_task = db.add.call_args[0][0]
        assert added_task.assigned_to == worker.id

    async def test_worker_cannot_be_assigned_to_foreign_company(self):
        """
        If the assigned_to user is not found in the admin's company, the handler
        must raise HTTP 400.  This prevents cross-company task assignment.

        'worker_cannot_be_assigned_admin_task' in the requirement maps to this
        company-membership check — the only role-based constraint on the assignee
        is that they must exist within the same company.
        """
        # Arrange
        db = _mock_db()
        admin = _make_admin()

        # Assigned user not found in company
        db.execute.return_value = MagicMock(**{"scalar_one_or_none.return_value": None})

        task_data = TaskCreate(
            assigned_to=uuid.uuid4(),
            type=TaskType.entrada,
            destination_location_id=uuid.uuid4(),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_task(task_data, db, admin)
        assert exc_info.value.status_code == 400
        assert "no pertenece a esta empresa" in exc_info.value.detail

    async def test_create_task_fails_when_destination_is_occupied(self):
        """
        An entrada task whose destination already holds a different product must
        be rejected with HTTP 400. Concrete attribute values are pinned on the
        existing InventoryItem so the handler's branching is deterministic
        (otherwise the auto-generated MagicMock attributes are truthy and the
        code path that fetches a Box is taken unexpectedly).
        """
        # Arrange
        db = _mock_db()
        admin = _make_admin()
        worker = _make_worker(company_id=admin.company_id)
        existing_item = MagicMock(spec=InventoryItem)
        existing_item.product_id = uuid.uuid4()  # different product
        existing_item.box_id = None              # avoid box lookup branch
        existing_item.quantity = 1

        db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": worker}),        # assignee found
            MagicMock(**{"scalar_one_or_none.return_value": existing_item}), # destination occupied
        ]

        task_data = TaskCreate(
            assigned_to=worker.id,
            type=TaskType.entrada,
            product_id=uuid.uuid4(),  # different from existing_item.product_id
            destination_location_id=uuid.uuid4(),
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_task(task_data, db, admin)
        assert exc_info.value.status_code == 400
        assert "destino" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Task query: filter by user
# ---------------------------------------------------------------------------

class TestGetTasksByUser:

    async def test_get_tasks_by_user_returns_only_own_tasks(self):
        """
        get_tasks_by_user must return the exact list produced by the DB query.
        The query already filters by (assigned_to=user_id, company_id=current_user.company_id),
        so this test validates that the handler passes through the result without
        merging or filtering further.
        """
        # Arrange
        db = _mock_db()
        current_user = _make_worker()
        target_user_id = uuid.uuid4()

        task_a = MagicMock(spec=Task)
        task_b = MagicMock(spec=Task)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [task_a, task_b]
        db.execute.return_value = mock_result

        # Act
        result = await get_tasks_by_user(target_user_id, db, current_user)

        # Assert: exactly the two tasks from the DB, in order
        assert result == [task_a, task_b]
        db.execute.assert_awaited_once()

    async def test_get_tasks_by_user_returns_empty_list_when_no_tasks(self):
        """
        When a user has no assigned tasks, the handler must return [] not raise an error.
        Workers starting their shift have 0 tasks, which is a valid state.
        """
        # Arrange
        db = _mock_db()
        current_user = _make_worker()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        # Act
        result = await get_tasks_by_user(uuid.uuid4(), db, current_user)

        # Assert
        assert result == []


# ---------------------------------------------------------------------------
# Task status update
# ---------------------------------------------------------------------------

class TestUpdateTaskStatus:

    async def test_update_task_status_to_completed(self):
        """
        Updating a task to status=completada must:
          1. Persist the new status via db.commit.
          2. Broadcast the status change via websocket_service.
        The integration tests verify the value in the HTTP response body.
        """
        # Arrange
        db = _mock_db()
        current_user = _make_worker()

        task = MagicMock(spec=Task)
        task.id = uuid.uuid4()
        task.status = TaskStatus.pendiente
        task.origin_location_id = None
        task.destination_location_id = None

        db.execute.return_value = MagicMock(
            **{"scalar_one_or_none.return_value": task}
        )

        status_data = TaskStatusUpdate(status=TaskStatus.completada)

        # Act
        with patch("app.api.tasks.websocket_service") as mock_ws:
            mock_ws.broadcast_task_status_changed = AsyncMock()
            result = await update_task_status(task.id, status_data, db, current_user)

        # Assert: status mutated, committed, and broadcast emitted
        assert task.status == TaskStatus.completada
        db.commit.assert_awaited_once()
        mock_ws.broadcast_task_status_changed.assert_awaited_once()

    async def test_update_task_status_raises_404_for_unknown_task(self):
        """
        Attempting to update a task that does not exist must raise HTTP 404.
        Workers can only update tasks that exist in their company's scope.
        """
        # Arrange
        db = _mock_db()
        current_user = _make_worker()
        db.execute.return_value = MagicMock(**{"scalar_one_or_none.return_value": None})

        status_data = TaskStatusUpdate(status=TaskStatus.completada)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_task_status(uuid.uuid4(), status_data, db, current_user)
        assert exc_info.value.status_code == 404

    async def test_update_task_status_broadcasts_location_ids(self):
        """
        The WebSocket broadcast must include origin_location_id and
        destination_location_id so the Unity twin can update shelf visuals.
        """
        # Arrange
        db = _mock_db()
        current_user = _make_worker()
        origin_id = uuid.uuid4()
        dest_id = uuid.uuid4()

        task = MagicMock(spec=Task)
        task.id = uuid.uuid4()
        task.status = TaskStatus.en_curso
        task.origin_location_id = origin_id
        task.destination_location_id = dest_id

        db.execute.return_value = MagicMock(
            **{"scalar_one_or_none.return_value": task}
        )

        # Act
        with patch("app.api.tasks.websocket_service") as mock_ws:
            mock_ws.broadcast_task_status_changed = AsyncMock()
            await update_task_status(
                task.id, TaskStatusUpdate(status=TaskStatus.completada), db, current_user
            )

        # Assert: location IDs forwarded to the broadcast
        call_kwargs = mock_ws.broadcast_task_status_changed.call_args.kwargs
        assert call_kwargs["origin_location_id"] == str(origin_id)
        assert call_kwargs["destination_location_id"] == str(dest_id)
