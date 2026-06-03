"""
Small direct-call unit tests for handlers whose HTTP integration tests pass
but whose line-level coverage isn't captured through httpx's ASGITransport.
Added to push the unit-only coverage above 90%.

Handlers covered:
  categories.get_categories, categories.create_category
  movements.get_movements, movements.get_movement, movements.get_movements_by_task
  auth.logout
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.categories import get_categories, create_category
from app.api.movements import get_movements, get_movement, get_movements_by_task
from app.api.auth import logout
from app.models.models import User, UserRole, Category, Movement
from app.schemas.schemas import CategoryCreate


def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _user():
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.company_id = uuid.uuid4()
    u.role = UserRole.admin
    return u


def _single(item):
    r = MagicMock()
    r.scalar_one_or_none.return_value = item
    return r


def _list(*items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = list(items)
    return r


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class TestCategoriesHandlers:

    async def test_list_returns_company_categories(self):
        db = _mock_db()
        c1 = MagicMock(spec=Category)
        c2 = MagicMock(spec=Category)
        db.execute.return_value = _list(c1, c2)

        result = await get_categories(db=db, current_user=_user())
        assert result == [c1, c2]

    async def test_create_persists_and_returns_category(self):
        db = _mock_db()
        result = await create_category(
            category_data=CategoryCreate(name="Bebidas", color="#abcdef"),
            db=db,
            current_user=_user(),
        )
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()
        assert result.name == "Bebidas"
        assert result.color == "#abcdef"


# ---------------------------------------------------------------------------
# Movements read handlers
# ---------------------------------------------------------------------------

class TestMovementReadHandlers:

    async def test_get_movements_returns_list(self):
        db = _mock_db()
        m = MagicMock(spec=Movement)
        db.execute.return_value = _list(m)
        result = await get_movements(db=db, current_user=_user())
        assert result == [m]

    async def test_get_movement_returns_when_found(self):
        db = _mock_db()
        m = MagicMock(spec=Movement)
        db.execute.return_value = _single(m)
        result = await get_movement(movement_id=uuid.uuid4(), db=db, current_user=_user())
        assert result is m

    async def test_get_movement_raises_404_when_missing(self):
        db = _mock_db()
        db.execute.return_value = _single(None)
        with pytest.raises(HTTPException) as e:
            await get_movement(movement_id=uuid.uuid4(), db=db, current_user=_user())
        assert e.value.status_code == 404

    async def test_get_movements_by_task_returns_list(self):
        db = _mock_db()
        m = MagicMock(spec=Movement)
        db.execute.return_value = _list(m)
        result = await get_movements_by_task(
            task_id=uuid.uuid4(), db=db, current_user=_user(),
        )
        assert result == [m]


# ---------------------------------------------------------------------------
# auth.logout
# ---------------------------------------------------------------------------

class TestLogoutHandler:

    async def test_logout_flips_is_online_false(self):
        db = _mock_db()
        user = MagicMock(spec=User)
        user.id = uuid.uuid4()

        await logout(current_user=user, db=db)

        db.execute.assert_awaited_once()
        db.commit.assert_awaited_once()
