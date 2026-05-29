#!/usr/bin/env python3
"""
seed_mock_stats.py
------------------
Genera datos mock para la seccion de Estadisticas.

    cd backend
    python seed_mock_stats.py          # crear datos
    python seed_mock_stats.py --clean  # borrar datos mock
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

# ── Perfiles
# Cada worker tiene:
#   (hoy, semana*, mes*, anteriores, pendientes_hoy, pendientes_atrasadas)
#   * semana = esta semana SIN contar hoy
#   * mes    = este mes SIN contar esta semana

MOCK_WORKERS = [
    {
        "name":     "Ana Garcia",
        "email":    "ana.garcia@mock.test",
        "profile":  (5, 8, 15, 12, 5, 1),
        "is_online": True,
    },
    {
        "name":     "Carlos Martinez",
        "email":    "carlos.martinez@mock.test",
        "profile":  (2, 5,  9,  6, 3, 2),
        "is_online": True,
    },
    {
        "name":     "Elena Lopez",
        "email":    "elena.lopez@mock.test",
        "profile":  (1, 2,  3,  2, 6, 3),
        "is_online": False,
    },
    {
        "name":     "Marcos Perez",
        "email":    "marcos.perez@mock.test",
        "profile":  (3, 7, 13,  8, 2, 0),
        "is_online": False,
    },
]

MOCK_EMAILS = {w["email"] for w in MOCK_WORKERS}
PASSWORD_HASH = get_password_hash("MockPass123!")


def rand_type():
    return random.choice(list(TaskType))

def rand_mov_type():
    return random.choice(list(MovementType))

def rand_in_range(start: datetime, end: datetime) -> datetime:
    delta = (end - start).total_seconds()
    return start + timedelta(seconds=random.uniform(0, delta))


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        result = await db.execute(
            select(User).where(User.role == UserRole.admin, User.is_active == True)
        )
        admin = result.scalars().first()
        if not admin:
            print("[ERROR] No hay ningun admin activo.")
            return

        company_id = admin.company_id
        print(f"[OK] Admin: {admin.email}\n")

        today       = date.today()
        now         = datetime.now()
        today_start = datetime.combine(today, datetime.min.time())
        week_start  = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
        month_start = datetime.combine(today.replace(day=1), datetime.min.time())

        # Ventanas de tiempo para cada bucket
        windows = {
            "today":  (today_start,              now),
            "week":   (week_start,               today_start),
            "month":  (month_start,              week_start),
            "old":    (now - timedelta(days=90), month_start),
        }

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
                    is_online=wdata["is_online"],
                    last_login=datetime.now() - timedelta(hours=random.uniform(0.5, 4)),
                )
                db.add(w)
                print(f"   [+] Worker creado: {wdata['name']}")
                workers.append(w)

        await db.flush()

        n_tasks = n_movs = 0

        for worker, wdata in zip(workers, MOCK_WORKERS):
            n_today, n_week, n_month, n_old, n_pend_hoy, n_pend_old = wdata["profile"]

            # Tareas completadas por bucket
            for bucket, count in [("today", n_today), ("week", n_week),
                                   ("month", n_month), ("old", n_old)]:
                win_start, win_end = windows[bucket]
                for _ in range(count):
                    created    = rand_in_range(win_start, win_end)
                    resolve_h  = random.uniform(0.25, 6)
                    completed  = min(created + timedelta(hours=resolve_h), now)

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

                    for _ in range(random.randint(1, 2)):
                        db.add(Movement(
                            id=uuid.uuid4(),
                            company_id=company_id,
                            task_id=task.id,
                            performed_by=worker.id,
                            type=rand_mov_type(),
                            timestamp=completed - timedelta(minutes=random.randint(1, 20)),
                        ))
                        n_movs += 1

            # Pendientes de hoy
            for _ in range(n_pend_hoy):
                created = rand_in_range(today_start, now)
                db.add(Task(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    created_by=admin.id,
                    assigned_to=worker.id,
                    type=rand_type(),
                    status=random.choice([TaskStatus.pendiente, TaskStatus.en_curso]),
                    created_at=created,
                ))
                n_tasks += 1

            # Pendientes atrasadas (creadas antes de hoy)
            for _ in range(n_pend_old):
                created = rand_in_range(windows["old"][0], today_start)
                db.add(Task(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    created_by=admin.id,
                    assigned_to=worker.id,
                    type=rand_type(),
                    status=TaskStatus.pendiente,
                    created_at=created,
                ))
                n_tasks += 1

        await db.commit()

    await engine.dispose()

    print(f"\n[OK] Seed completado: {len(workers)} workers, {n_tasks} tareas, {n_movs} movimientos")
    print("\n   Distribucion (hoy | semana | mes | antes | pend.hoy | atrasadas):")
    for wdata in MOCK_WORKERS:
        p = wdata["profile"]
        total = p[0] + p[1] + p[2] + p[3]
        print(f"   - {wdata['name']:20s}  {p[0]:2d} | {p[1]:2d} | {p[2]:2d} | {p[3]:2d} | {p[4]:2d} | {p[5]:2d}  (total completadas: {total})")
    print("\n   Contrasena: MockPass123!")


async def clean():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        result = await db.execute(select(User).where(User.email.in_(MOCK_EMAILS)))
        mock_workers = result.scalars().all()
        if not mock_workers:
            print("No hay datos mock que limpiar.")
            return

        mock_ids = [w.id for w in mock_workers]
        mov_r  = await db.execute(delete(Movement).where(Movement.performed_by.in_(mock_ids)))
        task_r = await db.execute(delete(Task).where(Task.assigned_to.in_(mock_ids)))
        for w in mock_workers:
            await db.delete(w)
        await db.commit()

    await engine.dispose()
    print(f"[OK] Limpieza: {len(mock_workers)} workers, {task_r.rowcount} tareas, {mov_r.rowcount} movimientos")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    asyncio.run(clean() if args.clean else seed())
