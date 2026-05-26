"""
Shared fixtures for the warehouse management system test suite.

Env vars must be set BEFORE any app module is imported because pydantic-settings
reads them at Settings() instantiation (which runs at app.core.config import time).
pytest_configure is too late — conftest module-level imports run first.

Architecture:
- test_engine (function scope): fresh in-memory SQLite DB per test for full isolation.
  StaticPool ensures every connection in a test shares the same in-memory DB.
- db_session: an AsyncSession bound to test_engine, used to insert/verify data directly.
- client: an httpx.AsyncClient with the FastAPI ASGI app, whose get_db dependency is
  overridden to use test_engine. All HTTP requests in a test hit the same DB as
  db_session because they share the same StaticPool engine.
- base_data: inserts one complete set of test entities and commits so the data is
  visible to all subsequent sessions/requests within the same test.
- admin_token / worker_token: valid JWT tokens generated with the same function the
  real app uses (create_access_token from app.core.security).
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!")

import uuid


from sqlalchemy.dialects.postgresql import UUID as _PG_UUID


def _pg_uuid_bind_sqlite(self, dialect):
    """
    Monkey-patch: make postgresql.UUID(as_uuid=True) work with SQLite.

    The original bind_processor calls ``value.hex``, which only works for
    Python uuid.UUID objects.  When a string UUID comes in (e.g. from a JWT
    payload or a Pydantic model), the call crashes on SQLite.
    This override accepts both uuid.UUID and str and stores a dashed string,
    which the existing result_processor can parse back into uuid.UUID.
    Only applied in the test process — production uses PostgreSQL natively.
    """
    if not self.as_uuid:
        return None

    def process(value):
        if value is not None:
            return str(value)  # uuid.UUID.__str__ → dashed form; str → as-is
        return value

    return process


_PG_UUID.bind_processor = _pg_uuid_bind_sqlite


import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import get_db, Base
from app.models.models import (
    User, UserRole, Company, Warehouse, Shelf, Level, Location, Product, Box,
)
from app.core.security import get_password_hash, create_access_token
from app.core import email as email_module

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Auto-mock external email (Resend) for every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _disable_external_email(monkeypatch):
    """
    Neutralise every send_*_email helper so no test hits the real Resend API.
    Applied automatically to all tests because none of the suite should reach
    out to a third-party service. Tests that need to assert an email was sent
    can re-patch the helper locally.
    """
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(email_module, "send_verification_email", _noop)
    monkeypatch.setattr(email_module, "send_temp_password_email", _noop)
    monkeypatch.setattr(email_module, "send_reset_password_email", _noop)
    # auth.py imports the helpers directly, so we also need to patch the
    # already-bound references in app.api.auth.
    import app.api.auth as auth_module
    monkeypatch.setattr(auth_module, "send_verification_email", _noop)
    monkeypatch.setattr(auth_module, "send_temp_password_email", _noop)
    monkeypatch.setattr(auth_module, "send_reset_password_email", _noop)


# ---------------------------------------------------------------------------
# Core infrastructure
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_engine():
    """
    Creates a fresh in-memory SQLite engine for each test function.
    StaticPool is required so that multiple AsyncSession objects within the same
    test all talk to the same in-memory DB (without it every new connection would
    get a separate, empty database).
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """AsyncSession connected to the test in-memory DB for direct data manipulation."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine):
    """
    httpx.AsyncClient with the FastAPI ASGI app.

    Overrides the get_db dependency so that every HTTP request uses a session
    from the same test_engine (and therefore the same StaticPool in-memory DB).
    The override is cleaned up after each test to avoid cross-test contamination.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Base test data
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def base_data(db_session):
    """
    Inserts a minimal but complete set of test entities and commits them so that
    every HTTP request in the test can find them (they share the same StaticPool DB).

    Structure
    ---------
    company ─┬─ admin (UserRole.admin)
             ├─ worker (UserRole.worker)
             └─ warehouse ── shelf ── level ─┬─ location1 (empty)
                                              └─ location2 (empty)
    product1 (barcode BAR001) ── box (10/20 units of product1)
    product2 (barcode BAR002)
    """
    company = Company(id=uuid.uuid4(), name="Test Company")
    db_session.add(company)
    await db_session.flush()

    admin = User(
        id=uuid.uuid4(),
        company_id=company.id,
        name="Admin Test",
        email="admin@test.com",
        password_hash=get_password_hash("admin123"),
        role=UserRole.admin,
        is_active=True,
        is_email_verified=True,
        must_change_password=False,
    )
    worker = User(
        id=uuid.uuid4(),
        company_id=company.id,
        name="Worker Test",
        email="worker@test.com",
        password_hash=get_password_hash("worker123"),
        role=UserRole.worker,
        is_active=True,
        is_email_verified=True,
        must_change_password=False,
    )
    db_session.add_all([admin, worker])
    await db_session.flush()

    warehouse = Warehouse(
        id=uuid.uuid4(),
        company_id=company.id,
        name="Test Warehouse",
        num_shelves=1,
        total_locations=2,
    )
    db_session.add(warehouse)
    await db_session.flush()

    shelf = Shelf(
        id=uuid.uuid4(),
        warehouse_id=warehouse.id,
        aisle_number=1,
        shelf_number=1,
    )
    db_session.add(shelf)
    await db_session.flush()

    level = Level(id=uuid.uuid4(), shelf_id=shelf.id, level_number=1)
    db_session.add(level)
    await db_session.flush()

    location1 = Location(id=uuid.uuid4(), level_id=level.id, position_number=1)
    location2 = Location(id=uuid.uuid4(), level_id=level.id, position_number=2)
    db_session.add_all([location1, location2])
    await db_session.flush()

    product1 = Product(
        id=uuid.uuid4(), company_id=company.id, name="Product Alpha", barcode="BAR001",
    )
    product2 = Product(
        id=uuid.uuid4(), company_id=company.id, name="Product Beta", barcode="BAR002",
    )
    db_session.add_all([product1, product2])
    await db_session.flush()

    box = Box(
        id=uuid.uuid4(),
        company_id=company.id,
        product_id=product1.id,
        current_quantity=10,
        max_capacity=20,
    )
    db_session.add(box)
    await db_session.commit()

    return {
        "company": company,
        "admin": admin,
        "worker": worker,
        "warehouse": warehouse,
        "shelf": shelf,
        "level": level,
        "location1": location1,
        "location2": location2,
        "product1": product1,
        "product2": product2,
        "box": box,
    }


# ---------------------------------------------------------------------------
# JWT token helpers
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def admin_token(base_data):
    """Valid JWT token for the test admin user, generated with the real security module."""
    admin = base_data["admin"]
    return create_access_token(data={
        "sub": str(admin.id),
        "role": admin.role.value,
        "company_id": str(admin.company_id),
        "must_change_password": admin.must_change_password,
    })


@pytest_asyncio.fixture
async def worker_token(base_data):
    """Valid JWT token for the test worker user, generated with the real security module."""
    worker = base_data["worker"]
    return create_access_token(data={
        "sub": str(worker.id),
        "role": worker.role.value,
        "company_id": str(worker.company_id),
        "must_change_password": worker.must_change_password,
    })
