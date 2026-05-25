#!/usr/bin/env python3
"""
seed_mock_stats.py
------------------
Genera datos mock para la sección de Estadísticas.

Ejecutar desde el directorio backend/ con el entorno virtual activo:

    cd backend
    python seed_mock_stats.py

Crea (de forma idempotente — si ya existen no los duplica):
  · 4 workers ficticios con perfiles de rendimiento distintos
  · ~101 tareas distribuidas en los últimos 30 días
  · ~90 movimientos asociados a tareas completadas

Para eliminar los datos mock luego:
    python seed_mock_stats.py --clean
"""

import asyncio
import random
import sys
import os
import argparse
from datetime import datetime, timedelta, date
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.models import (
    User, Task, Movement,
    UserRole, TaskType, TaskStatus, MovementType,
)

# ── Perfiles de workers mock ──────────────────────────────────────────────────
#  (n_completadas, n_pendientes_hoy, n_pendientes_old)

MOCK_WORKERS = [
    {
        "name":  "Ana García",
        "email": "ana.garcia@mock.test",
        "profile": (40, 5, 1),   # alto rendimiento, pocas deudas
    },
    {
        "name":  "Carlos Martínez",
        "email": "carlos.martinez@mock.test",
        "profile": (22, 3, 2),   # rendimiento medio
    },
    {
        "name":  "Elena López",
        "email": "elena.lopez@mock.test",
        "profile": (8, 6, 3),    # nueva/acumulación alta
    },
    {
        "name":  "Marcos Pérez",
        "email": "marcos.perez@mock.test",
        "profile": (31, 2, 0),   # constante y al día
    },
]

MOCK_EMAILS = {w["email"] for w in MOCK_WORKERS}
PASSWORD_HASH = get_password_hash("MockPass123!")

# ── Helpers ───────────────────────────────────────────────────────────────────

def rand_past(days_min: float, days_max: float) -> datetime:
    return datetime.utcnow() - timedelta(days=random.uniform(days_min, days_max))

def rand_type() -> TaskType:
    return random.choice(list(TaskType))

def rand_mov_type() -> MovementType:
    return random.choice(list(MovementType))

# ── Seed ─────────────────────────────────────────────────────────────────────

async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # Buscar admin activo
        result = await db.execute(
            select(User).where(User.role == UserRole.admin, User.is_active == True)
        )
        admin = result.scalars().first()
        if not admin:
            print("[ERROR] No hay ningun admin activo. Crea una cuenta primero.")
            return

        company_id = admin.company_id
        print(f"[OK] Admin: {admin.email}  |  company_id: {company_id}\n")

        today_start = datetime.combine(date.today(), datetime.min.time())

        workers: list[User] = []
        for wdata in MOCK_WORKERS:
            existing = (await db.execute(
                select(User).where(User.email == wdata["email"])
            )).scalar_one_or_none()

            if existing:
                print(f"   [=] Worker ya existe: {wdata['name']}")
                workers.append(existing)
            else:
                w = User(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    name=wdata["name"],
                    email=wdata["email"],
                    password_hash=PASSWORD_HASH,
                    role=UserRole.worker,
                    is_active=True,
                    is_email_verified=True,
                    must_change_password=False,
                    # login de hoy para que aparezcan en la recomendación
                    last_login=datetime.utcnow() - timedelta(hours=random.uniform(0.5, 5)),
                )
                db.add(w)
                print(f"   [+] Worker creado: {wdata['name']}")
                workers.append(w)

        await db.flush()

        n_tasks = n_movs = 0

        for worker, wdata in zip(workers, MOCK_WORKERS):
            n_done, n_pending_today, n_pending_old = wdata["profile"]

            # ── Tareas completadas (últimos 30 días) ─────────────────────────
            for _ in range(n_done):
                created = rand_past(1, 30)
                # Tiempo de resolución: entre 20 min y 8 h
                completed = created + timedelta(hours=random.uniform(0.33, 8))

                task = Task(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    created_by=admin.id,
                    assigned_to=worker.id,
                    type=rand_type(),
                    status=TaskStatus.completada,
                    created_at=created,
                    completed_at=completed,
                )
                db.add(task)
                n_tasks += 1

                # 1-2 movimientos por tarea
                for _ in range(random.randint(1, 2)):
                    db.add(Movement(
                        id=uuid.uuid4(),
                        company_id=company_id,
                        task_id=task.id,
                        performed_by=worker.id,
                        type=rand_mov_type(),
                        timestamp=completed - timedelta(minutes=random.randint(1, 25)),
                    ))
                    n_movs += 1

            # ── Tareas pendientes de HOY ─────────────────────────────────────
            for _ in range(n_pending_today):
                created = today_start + timedelta(hours=random.uniform(0, 9))
                task = Task(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    created_by=admin.id,
                    assigned_to=worker.id,
                    type=rand_type(),
                    status=random.choice([TaskStatus.pendiente, TaskStatus.en_curso]),
                    created_at=created,
                )
                db.add(task)
                n_tasks += 1

            # ── Tareas pendientes ANTIGUAS (atrasadas) ───────────────────────
            for _ in range(n_pending_old):
                created = rand_past(2, 7)
                task = Task(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    created_by=admin.id,
                    assigned_to=worker.id,
                    type=rand_type(),
                    status=TaskStatus.pendiente,
                    created_at=created,
                )
                db.add(task)
                n_tasks += 1

        await db.commit()

    await engine.dispose()

    print(f"\n[OK] Seed completado:")
    print(f"   - {len(workers)} workers")
    print(f"   - {n_tasks} tareas")
    print(f"   - {n_movs} movimientos")
    print(f"\n   Contrasena de todos los workers mock: MockPass123!")
    print(f"\n   Distribucion de workers:")
    for wdata in MOCK_WORKERS:
        d, p_hoy, p_old = wdata["profile"]
        print(f"   - {wdata['name']:20s} -> {d} completadas, {p_hoy} pendientes hoy, {p_old} atrasadas")


# ── Clean ─────────────────────────────────────────────────────────────────────

async def clean():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # Encontrar los workers mock
        result = await db.execute(
            select(User).where(User.email.in_(MOCK_EMAILS))
        )
        mock_workers = result.scalars().all()
        if not mock_workers:
            print("No hay datos mock que limpiar.")
            return

        mock_ids = [w.id for w in mock_workers]

        # Borrar movimientos
        mov_result = await db.execute(
            delete(Movement).where(Movement.performed_by.in_(mock_ids))
        )
        # Borrar tareas
        task_result = await db.execute(
            delete(Task).where(Task.assigned_to.in_(mock_ids))
        )
        # Borrar workers
        for w in mock_workers:
            await db.delete(w)

        await db.commit()
        print(f"[OK] Limpieza completada:")
        print(f"   - {len(mock_workers)} workers eliminados")
        print(f"   - {task_result.rowcount} tareas eliminadas")
        print(f"   - {mov_result.rowcount} movimientos eliminados")

    await engine.dispose()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Eliminar todos los datos mock")
    args = parser.parse_args()

    if args.clean:
        asyncio.run(clean())
    else:
        asyncio.run(seed())
