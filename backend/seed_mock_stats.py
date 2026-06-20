#!/usr/bin/env python3
"""
seed_mock_stats.py
------------------
Genera datos mock completos:
  - 4 workers con perfiles de actividad realistas
  - 7 categorias con colores distintivos
  - 10 productos con categoria, EAN-13 y limite de unidades/ubicacion
  - Limpia productos viejos sin categoria ni limite
  - Vacia y regenera el inventario completo del almacen
  - Tareas con ubicaciones reales mezcladas entre workers
  - Movimientos historicos

    cd backend
    python seed_mock_stats.py          # crear datos
    python seed_mock_stats.py --clean  # borrar todos los datos mock
"""

import asyncio
import random
import sys
import os
import argparse
from datetime import datetime, timedelta, date
import uuid
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.models import (
    User, Task, Movement, Product, InventoryItem, Category,
    Warehouse, Shelf, Level, Location,
    UserRole, TaskType, TaskStatus, MovementType,
)

# ── Workers ───────────────────────────────────────────────────────────────────

MOCK_WORKERS = [
    {"name": "Ana Garcia",      "email": "ana.garcia@mock.test",      "profile": (5, 8, 15, 12, 5, 1), "is_online": True},
    {"name": "Carlos Martinez", "email": "carlos.martinez@mock.test",  "profile": (2, 5,  9,  6, 3, 2), "is_online": True},
    {"name": "Elena Lopez",     "email": "elena.lopez@mock.test",      "profile": (1, 2,  3,  2, 6, 3), "is_online": False},
    {"name": "Marcos Perez",    "email": "marcos.perez@mock.test",     "profile": (3, 7, 13,  8, 2, 0), "is_online": False},
]
MOCK_WORKER_EMAILS = {w["email"] for w in MOCK_WORKERS}

# ── Categorias ────────────────────────────────────────────────────────────────

MOCK_CATEGORIES = [
    {"name": "Ferreteria",   "color": "#E67E22"},
    {"name": "Embalaje",     "color": "#3498DB"},
    {"name": "Alimentacion", "color": "#2ECC71"},
    {"name": "Oficina",      "color": "#9B59B6"},
    {"name": "EPI",          "color": "#E74C3C"},
    {"name": "Electricidad", "color": "#F1C40F"},
    {"name": "Metal",        "color": "#7F8C8D"},
]
MOCK_CATEGORY_NAMES = {c["name"] for c in MOCK_CATEGORIES}

# ── Productos ─────────────────────────────────────────────────────────────────

MOCK_PRODUCTS = [
    {"name": "Caja tornillos M8 (100 ud)",       "barcode": "8410076470261", "type": "Ferreteria",   "description": "Tornillos metrica 8 con tuerca, 100 unidades por caja", "category": "Ferreteria",   "units_per_location": 20},
    {"name": "Rollo cinta adhesiva 48 mm",        "barcode": "8410876234510", "type": "Embalaje",     "description": "Cinta adhesiva transparente de embalaje, rollo 66 m",   "category": "Embalaje",     "units_per_location": 50},
    {"name": "Palet botellas agua 1.5 L",         "barcode": "8437003456782", "type": "Alimentacion", "description": "Agua mineral natural, palet de 48 botellas",            "category": "Alimentacion", "units_per_location": 4},
    {"name": "Caja papel A4 500 hojas",           "barcode": "8410056789013", "type": "Oficina",      "description": "Papel blanco 80 g/m2, 500 hojas por caja",             "category": "Oficina",      "units_per_location": 10},
    {"name": "Guantes trabajo talla M",           "barcode": "8410765432104", "type": "EPI",          "description": "Guantes de proteccion mecanica nivel 2, par",           "category": "EPI",          "units_per_location": 30},
    {"name": "Bombilla LED E27 10 W",             "barcode": "8410234567895", "type": "Electricidad", "description": "Bombilla LED luz fria 6500 K, casquillo E27",           "category": "Electricidad", "units_per_location": 24},
    {"name": "Palet conservas tomate 400 g",      "barcode": "8437654321086", "type": "Alimentacion", "description": "Tomate triturado en lata 400 g, palet 120 unidades",    "category": "Alimentacion", "units_per_location": 4},
    {"name": "Cinta precinto rojo 50 mm",         "barcode": "8410987654327", "type": "Embalaje",     "description": "Precinto de seguridad color rojo, bobina 66 m",         "category": "Embalaje",     "units_per_location": 40},
    {"name": "Barra acero 1 m diametro 20 mm",   "barcode": "8410345678908", "type": "Metal",        "description": "Barra redonda de acero S235, longitud 1 metro",         "category": "Metal",        "units_per_location": 8},
    {"name": "Caja guantes nitrilo (100 ud)",     "barcode": "8410123456799", "type": "EPI",          "description": "Guantes desechables de nitrilo sin polvo, caja 100 ud", "category": "EPI",          "units_per_location": 20},
]
MOCK_PRODUCT_BARCODES = {p["barcode"] for p in MOCK_PRODUCTS}

PASSWORD_HASH = get_password_hash("MockPass123!")

# No crear tareas falsas para forzar la visualizacion.
# Las unidades deben salir del inventario real, no de tareas activas.
CREATE_ACTIVE_TASK_PER_OCCUPIED_LOCATION = False


def get_async_database_url():
    """
    Convierte la URL de PostgreSQL de Railway al formato compatible
    con SQLAlchemy async + asyncpg.
    """
    db_url = settings.DATABASE_URL

    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return db_url


# ── Utilidades ────────────────────────────────────────────────────────────────

def rand_in_range(start: datetime, end: datetime) -> datetime:
    delta = max((end - start).total_seconds(), 1)
    return start + timedelta(seconds=random.uniform(0, delta))


def task_type_for_movement(tt: TaskType) -> MovementType:
    return {
        TaskType.entrada:  MovementType.entrada,
        TaskType.salida:   MovementType.salida,
        TaskType.traslado: MovementType.traslado,
    }[tt]


# ── Seed ──────────────────────────────────────────────────────────────────────

async def seed():
    engine  = create_async_engine(get_async_database_url(), echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:

        # 1. Admin activo
        admin = (await db.execute(
            select(User).where(User.role == UserRole.admin, User.is_active == True)
        )).scalars().first()
        if not admin:
            print("[ERROR] No hay ningun admin activo.")
            return
        company_id = admin.company_id
        print(f"[OK] Admin: {admin.email}\n")

        # 2. Workers
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
                    id=uuid.uuid4(), company_id=company_id,
                    name=wdata["name"], email=wdata["email"],
                    password_hash=PASSWORD_HASH, role=UserRole.worker,
                    is_active=True, is_email_verified=True,
                    must_change_password=False, is_online=wdata["is_online"],
                    last_login=datetime.now() - timedelta(hours=random.uniform(0.5, 4)),
                )
                db.add(w)
                print(f"   [+] Worker creado: {wdata['name']}")
                workers.append(w)
        await db.flush()

        # 3. Categorias
        cat_map: dict[str, uuid.UUID] = {}
        for cdata in MOCK_CATEGORIES:
            existing_c = (await db.execute(
                select(Category).where(
                    Category.name == cdata["name"],
                    Category.company_id == company_id,
                )
            )).scalar_one_or_none()
            if existing_c:
                print(f"   [=] Categoria ya existe: {cdata['name']}")
                cat_map[cdata["name"]] = existing_c.id
            else:
                c = Category(
                    id=uuid.uuid4(), company_id=company_id,
                    name=cdata["name"], color=cdata["color"],
                )
                db.add(c)
                cat_map[cdata["name"]] = c.id
                print(f"   [+] Categoria creada: {cdata['name']}  {cdata['color']}")
        await db.flush()

        # 4. Limpiar productos viejos sin categoria ni unidades maximas
        #    (los que existian antes del seed y no son productos mock)
        old_products = (await db.execute(
            select(Product).where(
                Product.company_id == company_id,
                Product.category_id == None,
                Product.units_per_location == None,
                Product.barcode.notin_(MOCK_PRODUCT_BARCODES),
            )
        )).scalars().all()
        if old_products:
            old_ids = [p.id for p in old_products]
            inv_deleted = await db.execute(
                delete(InventoryItem).where(InventoryItem.product_id.in_(old_ids))
            )
            for p in old_products:
                await db.delete(p)
            await db.flush()
            print(f"\n   [~] Productos viejos eliminados: {len(old_products)}"
                  f"  (+ {inv_deleted.rowcount} items de inventario)")
        else:
            print(f"\n   [=] No habia productos viejos sin categoria")

        # 5. Crear / reutilizar productos mock
        products: list[Product] = []
        prod_upl: dict[uuid.UUID, int] = {}
        for pdata in MOCK_PRODUCTS:
            existing_p = (await db.execute(
                select(Product).where(Product.barcode == pdata["barcode"])
            )).scalar_one_or_none()
            if existing_p:
                # Actualizar tambien los productos existentes para asegurar que
                # tienen categoria y unidades maximas por ubicacion.
                existing_p.name = pdata["name"]
                existing_p.type = pdata["type"]
                existing_p.description = pdata["description"]
                existing_p.category_id = cat_map.get(pdata["category"])
                existing_p.units_per_location = pdata["units_per_location"]
                print(f"   [=] Producto actualizado: {pdata['name']}"
                      f"  |  max {pdata['units_per_location']} ud/ubic"
                      f"  |  {pdata['category']}")
                products.append(existing_p)
                prod_upl[existing_p.id] = pdata["units_per_location"]
            else:
                p = Product(
                    id=uuid.uuid4(), company_id=company_id,
                    name=pdata["name"], barcode=pdata["barcode"],
                    type=pdata["type"], description=pdata["description"],
                    category_id=cat_map.get(pdata["category"]),
                    units_per_location=pdata["units_per_location"],
                )
                db.add(p)
                prod_upl[p.id] = pdata["units_per_location"]
                print(f"   [+] Producto: {pdata['name']}"
                      f"  |  {pdata['barcode']}"
                      f"  |  max {pdata['units_per_location']} ud/ubic"
                      f"  |  {pdata['category']}")
                products.append(p)
        await db.flush()

        # 6. Obtener todas las ubicaciones del almacen
        wh = (await db.execute(
            select(Warehouse).where(Warehouse.company_id == company_id)
        )).scalars().first()

        all_location_ids: list[uuid.UUID] = []
        if wh:
            shelves = (await db.execute(
                select(Shelf).where(Shelf.warehouse_id == wh.id)
            )).scalars().all()
            shelf_ids = [s.id for s in shelves]
            if shelf_ids:
                levels = (await db.execute(
                    select(Level).where(Level.shelf_id.in_(shelf_ids))
                )).scalars().all()
                level_ids = [lv.id for lv in levels]
                if level_ids:
                    locs = (await db.execute(
                        select(Location).where(Location.level_id.in_(level_ids))
                    )).scalars().all()
                    all_location_ids = [loc.id for loc in locs]

        print(f"\n   Ubicaciones en el almacen: {len(all_location_ids)}")

        # 7. Vaciar TODO el inventario del almacen y regenerarlo con los productos mock
        if all_location_ids:
            wiped = await db.execute(
                delete(InventoryItem).where(InventoryItem.location_id.in_(all_location_ids))
            )
            await db.flush()
            print(f"   [~] Inventario anterior vaciado: {wiped.rowcount} items eliminados")

        # Crear inventario nuevo en ~42% de ubicaciones
        # prod_summary[prod_name] = {"locs": int, "units": int}
        prod_summary: dict[str, dict] = defaultdict(lambda: {"locs": 0, "units": 0})

        occupied_locs: list[tuple] = []   # [(location_id, product_id, quantity)]
        free_locs     = list(all_location_ids)

        if all_location_ids and products:
            random.shuffle(free_locs)
            n_to_fill = max(1, int(len(free_locs) * 0.42))
            locs_to_fill = free_locs[:n_to_fill]

            for loc_id in locs_to_fill:
                product = random.choice(products)
                upl     = prod_upl.get(product.id, 8)
                qty     = random.randint(1, upl)
                db.add(InventoryItem(
                    id=uuid.uuid4(),
                    location_id=loc_id,
                    product_id=product.id,
                    quantity=qty,
                ))
                occupied_locs.append((loc_id, product.id, qty))
                prod_summary[product.name]["locs"]  += 1
                prod_summary[product.name]["units"] += qty

            await db.flush()
            free_locs = [loc for loc in all_location_ids
                         if loc not in {o[0] for o in occupied_locs}]

            print(f"\n   INVENTARIO  ({len(occupied_locs)} ubicaciones ocupadas"
                  f" / {len(free_locs)} libres / {len(all_location_ids)} total)")
            print(f"   {'Producto':<40} {'Ubic.':>6}  {'Uds.':>6}  {'Max/ubic':>9}")
            print(f"   {'-'*40}  {'-'*6}  {'-'*6}  {'-'*9}")
            for pdata in MOCK_PRODUCTS:
                s   = prod_summary.get(pdata["name"], {"locs": 0, "units": 0})
                upl = pdata["units_per_location"]
                print(f"   {pdata['name']:<40} {s['locs']:>6}  {s['units']:>6}  {upl:>9}")
        else:
            print("   [!] Sin almacen o sin productos — inventario no generado")

        # 8. Construir tareas y mezclarlas entre workers
        today       = date.today()
        now         = datetime.now()
        today_start = datetime.combine(today, datetime.min.time())
        week_start  = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
        month_start = datetime.combine(today.replace(day=1), datetime.min.time())
        windows = {
            "today": (today_start, now),
            "week":  (week_start,  today_start),
            "month": (month_start, week_start),
            "old":   (now - timedelta(days=90), month_start),
        }

        task_specs: list[dict] = []
        for worker, wdata in zip(workers, MOCK_WORKERS):
            n_today, n_week, n_month, n_old, n_pend_hoy, n_pend_old = wdata["profile"]
            for bucket, count in [("today", n_today), ("week", n_week),
                                   ("month", n_month), ("old", n_old)]:
                ws, we = windows[bucket]
                for _ in range(count):
                    created   = rand_in_range(ws, we)
                    completed = min(created + timedelta(hours=random.uniform(0.25, 6)), now)
                    task_specs.append({"worker": worker, "type": random.choice(list(TaskType)),
                                       "status": TaskStatus.completada,
                                       "created": created, "completed": completed})
            for _ in range(n_pend_hoy):
                task_specs.append({"worker": worker, "type": random.choice(list(TaskType)),
                                   "status": random.choice([TaskStatus.pendiente, TaskStatus.en_curso]),
                                   "created": rand_in_range(today_start, now), "completed": None})
            for _ in range(n_pend_old):
                task_specs.append({"worker": worker, "type": random.choice(list(TaskType)),
                                   "status": TaskStatus.pendiente,
                                   "created": rand_in_range(windows["old"][0], today_start),
                                   "completed": None})

        random.shuffle(task_specs)   # mezclar workers

        # 9. Insertar tareas con ubicaciones reales
        occ_pool  = list(occupied_locs)
        free_pool = list(free_locs)
        random.shuffle(occ_pool)
        random.shuffle(free_pool)

        n_tasks = n_movs = 0

        # 9.1. Tareas activas para que la vista del almacen pueda mostrar
        #      las unidades de TODOS los huecos con producto.
        #      Algunas vistas usan la cantidad de la tarea activa para pintar
        #      el texto del hueco; por eso copiamos la cantidad real del
        #      InventoryItem en una tarea en_curso.
        if CREATE_ACTIVE_TASK_PER_OCCUPIED_LOCATION and occupied_locs and workers:
            online_workers = [w for w, wdata in zip(workers, MOCK_WORKERS) if wdata["is_online"]] or workers
            for idx, (loc_id, product_id, qty) in enumerate(occupied_locs):
                worker = online_workers[idx % len(online_workers)]
                task = Task(
                    id=uuid.uuid4(), company_id=company_id,
                    created_by=admin.id, assigned_to=worker.id,
                    type=TaskType.salida, status=TaskStatus.en_curso,
                    origin_location_id=loc_id,
                    destination_location_id=None,
                    product_id=product_id,
                    quantity=qty,
                    created_at=now - timedelta(minutes=random.randint(3, 90)),
                    completed_at=None,
                )
                db.add(task)
                n_tasks += 1
            await db.flush()
            print(f"\n   [+] Tareas activas de inventario: {len(occupied_locs)} "
                  f"(para mostrar unidades en todos los huecos ocupados)")

        def pick_occ():
            return occ_pool[random.randint(0, len(occ_pool) - 1)] if occ_pool else None

        def pick_free():
            return free_pool[random.randint(0, len(free_pool) - 1)] if free_pool else None

        for spec in task_specs:
            worker  = spec["worker"]
            ttype   = spec["type"]
            tstatus = spec["status"]
            created = spec["created"]
            completed = spec["completed"]
            origin_loc_id = dest_loc_id = product_id = quantity = None

            if ttype == TaskType.entrada:
                f = pick_free()
                if f:
                    p = random.choice(products)
                    dest_loc_id = f
                    product_id  = p.id
                    quantity    = random.randint(1, prod_upl.get(p.id, 5))
            elif ttype == TaskType.salida:
                o = pick_occ()
                if o:
                    origin_loc_id = o[0]
                    product_id    = o[1]
                    quantity      = random.randint(1, max(1, o[2]))
            elif ttype == TaskType.traslado:
                o = pick_occ()
                f = pick_free()
                if o and f and o[0] != f:
                    origin_loc_id = o[0]
                    dest_loc_id   = f
                    product_id    = o[1]

            task = Task(
                id=uuid.uuid4(), company_id=company_id,
                created_by=admin.id, assigned_to=worker.id,
                type=ttype, status=tstatus,
                origin_location_id=origin_loc_id,
                destination_location_id=dest_loc_id,
                product_id=product_id, quantity=quantity,
                created_at=created, completed_at=completed,
            )
            db.add(task)
            n_tasks += 1

            if tstatus == TaskStatus.completada and completed:
                for _ in range(random.randint(1, 2)):
                    db.add(Movement(
                        id=uuid.uuid4(), company_id=company_id,
                        task_id=task.id, performed_by=worker.id,
                        type=task_type_for_movement(ttype),
                        product_id=product_id,
                        origin_location_id=origin_loc_id,
                        destination_location_id=dest_loc_id,
                        quantity=quantity,
                        timestamp=completed - timedelta(minutes=random.randint(1, 20)),
                    ))
                    n_movs += 1

        await db.commit()

    await engine.dispose()

    print(f"\n[OK] Seed completado:")
    print(f"   Workers      : {len(workers)}")
    print(f"   Categorias   : {len(cat_map)}")
    print(f"   Productos    : {len(products)}")
    print(f"   Tareas       : {n_tasks}  (mezcladas entre workers)")
    print(f"   Movimientos  : {n_movs}")
    print(f"\n   Contrasena workers: MockPass123!")


# ── Clean ─────────────────────────────────────────────────────────────────────

async def clean():
    engine = create_async_engine(get_async_database_url(), echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # 1. Localizar workers mock
        mock_workers = (await db.execute(
            select(User).where(User.email.in_(MOCK_WORKER_EMAILS))
        )).scalars().all()

        worker_ids = [w.id for w in mock_workers]

        # 2. Localizar productos mock
        mock_products = (await db.execute(
            select(Product).where(Product.barcode.in_(MOCK_PRODUCT_BARCODES))
        )).scalars().all()

        product_ids = [p.id for p in mock_products]

        # 3. Localizar tareas mock:
        #    - tareas asignadas a workers mock
        #    - tareas asociadas a productos mock
        task_ids = set()

        if worker_ids:
            result = await db.execute(
                select(Task.id).where(Task.assigned_to.in_(worker_ids))
            )
            task_ids.update(result.scalars().all())

        if product_ids:
            result = await db.execute(
                select(Task.id).where(Task.product_id.in_(product_ids))
            )
            task_ids.update(result.scalars().all())

        task_ids = list(task_ids)

        # 4. Borrar movimientos ANTES de borrar tareas/productos
        movements_deleted = 0

        if task_ids:
            result = await db.execute(
                delete(Movement).where(Movement.task_id.in_(task_ids))
            )
            movements_deleted += result.rowcount or 0

        if worker_ids:
            result = await db.execute(
                delete(Movement).where(Movement.performed_by.in_(worker_ids))
            )
            movements_deleted += result.rowcount or 0

        if product_ids:
            result = await db.execute(
                delete(Movement).where(Movement.product_id.in_(product_ids))
            )
            movements_deleted += result.rowcount or 0

        # 5. Borrar tareas
        tasks_deleted = 0

        if task_ids:
            result = await db.execute(
                delete(Task).where(Task.id.in_(task_ids))
            )
            tasks_deleted += result.rowcount or 0

        # Por seguridad, repetir filtros directos por si queda alguna tarea suelta
        if worker_ids:
            result = await db.execute(
                delete(Task).where(Task.assigned_to.in_(worker_ids))
            )
            tasks_deleted += result.rowcount or 0

        if product_ids:
            result = await db.execute(
                delete(Task).where(Task.product_id.in_(product_ids))
            )
            tasks_deleted += result.rowcount or 0

        # 6. Borrar inventario de productos mock
        inventory_deleted = 0

        if product_ids:
            result = await db.execute(
                delete(InventoryItem).where(InventoryItem.product_id.in_(product_ids))
            )
            inventory_deleted += result.rowcount or 0

        # 7. Borrar productos mock
        products_deleted = 0

        if product_ids:
            result = await db.execute(
                delete(Product).where(Product.id.in_(product_ids))
            )
            products_deleted += result.rowcount or 0

        # 8. Borrar workers mock
        workers_deleted = 0

        if worker_ids:
            result = await db.execute(
                delete(User).where(User.id.in_(worker_ids))
            )
            workers_deleted += result.rowcount or 0

        # 9. Borrar categorías mock solo si ya no tienen productos asociados
        categories_deleted = 0

        mock_cats = (await db.execute(
            select(Category).where(Category.name.in_(MOCK_CATEGORY_NAMES))
        )).scalars().all()

        for category in mock_cats:
            product_using_category = (await db.execute(
                select(Product.id)
                .where(Product.category_id == category.id)
                .limit(1)
            )).scalar_one_or_none()

            if product_using_category is None:
                await db.delete(category)
                categories_deleted += 1

        await db.commit()

        print("[OK] Limpieza completada")
        print(f"   Movimientos eliminados : {movements_deleted}")
        print(f"   Tareas eliminadas      : {tasks_deleted}")
        print(f"   Inventario eliminado   : {inventory_deleted}")
        print(f"   Productos eliminados   : {products_deleted}")
        print(f"   Workers eliminados     : {workers_deleted}")
        print(f"   Categorias eliminadas  : {categories_deleted}")

    await engine.dispose()

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Eliminar datos mock")
    args = parser.parse_args()
    asyncio.run(clean() if args.clean else seed())
