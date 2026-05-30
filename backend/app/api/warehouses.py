from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Warehouse, Shelf, Level, Location, InventoryItem, Product, Category, Task, TaskStatus
from app.schemas.schemas import (
    WarehouseCreate, WarehouseNameUpdate, WarehouseExpand, WarehouseResponse, WarehouseFullResponse,
    ShelfFullResponse, LevelFullResponse, LocationFullResponse,
    InventoryItemFullResponse
)
from app.api.deps import get_current_admin
import uuid

router = APIRouter(prefix="/warehouses", tags=["warehouses"])

@router.get("", response_model=list[WarehouseResponse])
async def get_warehouses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Warehouse).where(Warehouse.company_id == current_user.company_id)
    )
    return result.scalars().all()


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    total_locations = sum(
        (2 if s.is_double else 1) * s.num_levels * s.num_locations
        for aisle in warehouse_data.aisles
        for s in aisle.shelves
    )
    num_shelves = sum(
        (2 if s.is_double else 1)
        for aisle in warehouse_data.aisles
        for s in aisle.shelves
    )

    warehouse = Warehouse(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        name=warehouse_data.name,
        num_shelves=num_shelves,
        num_levels=None,
        num_locations=None,
        total_locations=total_locations,
    )
    db.add(warehouse)

    db_aisle = 1
    for aisle_cfg in warehouse_data.aisles:
        # --- Estanterías frontales (o simples) ---
        for front_num, shelf_cfg in enumerate(aisle_cfg.shelves, start=1):
            shelf = Shelf(
                id=uuid.uuid4(),
                warehouse_id=warehouse.id,
                aisle_number=db_aisle,
                shelf_number=front_num,
                is_double=shelf_cfg.is_double,
            )
            db.add(shelf)
            for level_num in range(1, shelf_cfg.num_levels + 1):
                level = Level(id=uuid.uuid4(), shelf_id=shelf.id, level_number=level_num)
                db.add(level)
                for pos in range(1, shelf_cfg.num_locations + 1):
                    db.add(Location(id=uuid.uuid4(), level_id=level.id, position_number=pos))
        db_aisle += 1

        # --- Estanterías traseras: fila propia con shelf_number desde 1 ---
        double_shelves = [s for s in aisle_cfg.shelves if s.is_double]
        if double_shelves:
            for back_num, shelf_cfg in enumerate(double_shelves, start=1):
                back_shelf = Shelf(
                    id=uuid.uuid4(),
                    warehouse_id=warehouse.id,
                    aisle_number=db_aisle,
                    shelf_number=back_num,
                    is_double=False,
                )
                db.add(back_shelf)
                for level_num in range(1, shelf_cfg.num_levels + 1):
                    level = Level(id=uuid.uuid4(), shelf_id=back_shelf.id, level_number=level_num)
                    db.add(level)
                    for pos in range(1, shelf_cfg.num_locations + 1):
                        db.add(Location(id=uuid.uuid4(), level_id=level.id, position_number=pos))
            db_aisle += 1

    await db.commit()
    await db.refresh(warehouse)
    return warehouse


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(
    warehouse_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.company_id == current_user.company_id
        )
    )
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado")
    return warehouse


@router.get("/{warehouse_id}/full", response_model=WarehouseFullResponse)
async def get_warehouse_full(
    warehouse_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.company_id == current_user.company_id
        )
    )
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Almacén no encontrado")

    shelves_result = await db.execute(
        select(Shelf).where(Shelf.warehouse_id == warehouse_id)
        .order_by(Shelf.aisle_number, Shelf.shelf_number)
    )
    shelves = shelves_result.scalars().all()

    shelf_ids = [s.id for s in shelves]
    levels_result = await db.execute(
        select(Level).where(Level.shelf_id.in_(shelf_ids))
    )
    levels = levels_result.scalars().all()

    level_ids = [l.id for l in levels]
    locations_result = await db.execute(
        select(Location).where(Location.level_id.in_(level_ids))
    )
    locations = locations_result.scalars().all()

    location_ids = [loc.id for loc in locations]
    inventory_result = await db.execute(
        select(InventoryItem).where(InventoryItem.location_id.in_(location_ids))
    )
    inventory_items = inventory_result.scalars().all()

    all_product_ids = list({item.product_id for item in inventory_items})
    products_by_id = {}
    if all_product_ids:
        products_result = await db.execute(select(Product).where(Product.id.in_(all_product_ids)))
        products_by_id = {p.id: p for p in products_result.scalars().all()}

    category_ids = list({p.category_id for p in products_by_id.values() if p.category_id})
    categories_by_id = {}
    if category_ids:
        categories_result = await db.execute(select(Category).where(Category.id.in_(category_ids)))
        categories_by_id = {c.id: c for c in categories_result.scalars().all()}

    inventory_by_location = {item.location_id: item for item in inventory_items}
    locations_by_level = {}
    for loc in locations:
        locations_by_level.setdefault(loc.level_id, []).append(loc)
    levels_by_shelf = {}
    for level in levels:
        levels_by_shelf.setdefault(level.shelf_id, []).append(level)

    shelves_full = []
    for shelf in shelves:
        levels_full = []
        for level in levels_by_shelf.get(shelf.id, []):
            locations_full = []
            for loc in locations_by_level.get(level.id, []):
                inv = inventory_by_location.get(loc.id)
                if inv:
                    product = products_by_id.get(inv.product_id)
                    category = categories_by_id.get(product.category_id) if product and product.category_id else None
                    inventory_dto = InventoryItemFullResponse(
                        id=inv.id,
                        product_id=inv.product_id,
                        product_name=product.name if product else None,
                        product_barcode=product.barcode if product else None,
                        product_category=category.name if category else None,
                        product_category_color=category.color if category else None,
                        quantity=inv.quantity,
                    )
                else:
                    inventory_dto = None

                locations_full.append(LocationFullResponse(
                    id=loc.id,
                    position_number=loc.position_number,
                    nfc_tag=loc.nfc_tag,
                    inventory=inventory_dto
                ))

            levels_full.append(LevelFullResponse(
                id=level.id,
                level_number=level.level_number,
                locations=locations_full
            ))

        shelves_full.append(ShelfFullResponse(
            id=shelf.id,
            aisle_number=shelf.aisle_number,
            shelf_number=shelf.shelf_number,
            is_double=shelf.is_double,
            levels=levels_full
        ))

    tasks_result = await db.execute(
        select(Task).where(
            Task.company_id == current_user.company_id,
            Task.status.in_([TaskStatus.pendiente, TaskStatus.en_curso])
        )
    )
    active_tasks = tasks_result.scalars().all()
    active_task_locations = list({
        str(loc_id)
        for task in active_tasks
        for loc_id in (task.origin_location_id, task.destination_location_id)
        if loc_id is not None
    })
    active_task_info = {}
    for task in active_tasks:
        if task.origin_location_id:
            active_task_info[str(task.origin_location_id)] = task.type.value
        if task.destination_location_id:
            active_task_info[str(task.destination_location_id)] = task.type.value

    return WarehouseFullResponse(
        id=warehouse.id,
        name=warehouse.name,
        num_shelves=warehouse.num_shelves,
        num_levels=warehouse.num_levels,
        num_locations=warehouse.num_locations,
        total_locations=warehouse.total_locations,
        created_at=warehouse.created_at,
        shelves=shelves_full,
        active_task_locations=active_task_locations,
        active_task_info=active_task_info,
    )


@router.post("/{warehouse_id}/expand", response_model=WarehouseResponse)
async def expand_warehouse(
    warehouse_id: uuid.UUID,
    expand_data: WarehouseExpand,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.company_id == current_user.company_id
        )
    )
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Almacén no encontrado")

    shelves_result = await db.execute(
        select(Shelf).where(Shelf.warehouse_id == warehouse_id)
    )
    existing_shelves = shelves_result.scalars().all()

    new_shelf_count = 0
    new_location_count = 0

    # 1. Ampliar filas existentes
    sorted_aisle_nums = sorted(set(s.aisle_number for s in existing_shelves))
    for ext in expand_data.extend_aisles:
        aisle_num = ext.aisle_number
        aisle_shelves = [s for s in existing_shelves if s.aisle_number == aisle_num]
        if not aisle_shelves:
            raise HTTPException(status_code=400, detail=f"Fila {aisle_num} no encontrada")

        is_double = any(s.is_double for s in aisle_shelves)
        max_shelf_num = max(s.shelf_number for s in aisle_shelves)

        back_aisle_num = None
        if is_double:
            idx = sorted_aisle_nums.index(aisle_num)
            if idx + 1 < len(sorted_aisle_nums):
                back_aisle_num = sorted_aisle_nums[idx + 1]

        for i, shelf_cfg in enumerate(ext.new_shelves, start=1):
            new_shelf_num = max_shelf_num + i
            shelf = Shelf(
                id=uuid.uuid4(), warehouse_id=warehouse_id,
                aisle_number=aisle_num, shelf_number=new_shelf_num, is_double=is_double,
            )
            db.add(shelf)
            new_shelf_count += 1
            for level_num in range(1, shelf_cfg.num_levels + 1):
                level = Level(id=uuid.uuid4(), shelf_id=shelf.id, level_number=level_num)
                db.add(level)
                for pos in range(1, shelf_cfg.num_locations + 1):
                    db.add(Location(id=uuid.uuid4(), level_id=level.id, position_number=pos))
                    new_location_count += 1

            if is_double and back_aisle_num:
                back_shelf = Shelf(
                    id=uuid.uuid4(), warehouse_id=warehouse_id,
                    aisle_number=back_aisle_num, shelf_number=new_shelf_num, is_double=False,
                )
                db.add(back_shelf)
                new_shelf_count += 1
                for level_num in range(1, shelf_cfg.num_levels + 1):
                    level = Level(id=uuid.uuid4(), shelf_id=back_shelf.id, level_number=level_num)
                    db.add(level)
                    for pos in range(1, shelf_cfg.num_locations + 1):
                        db.add(Location(id=uuid.uuid4(), level_id=level.id, position_number=pos))
                        new_location_count += 1

    # 2. Añadir filas nuevas
    db_aisle = (max(s.aisle_number for s in existing_shelves) + 1) if existing_shelves else 1
    for aisle_cfg in expand_data.new_aisles:
        for front_num, shelf_cfg in enumerate(aisle_cfg.shelves, start=1):
            shelf = Shelf(
                id=uuid.uuid4(), warehouse_id=warehouse_id,
                aisle_number=db_aisle, shelf_number=front_num, is_double=shelf_cfg.is_double,
            )
            db.add(shelf)
            new_shelf_count += 1
            for level_num in range(1, shelf_cfg.num_levels + 1):
                level = Level(id=uuid.uuid4(), shelf_id=shelf.id, level_number=level_num)
                db.add(level)
                for pos in range(1, shelf_cfg.num_locations + 1):
                    db.add(Location(id=uuid.uuid4(), level_id=level.id, position_number=pos))
                    new_location_count += 1
        db_aisle += 1

        double_shelves = [s for s in aisle_cfg.shelves if s.is_double]
        if double_shelves:
            for back_num, shelf_cfg in enumerate(double_shelves, start=1):
                back_shelf = Shelf(
                    id=uuid.uuid4(), warehouse_id=warehouse_id,
                    aisle_number=db_aisle, shelf_number=back_num, is_double=False,
                )
                db.add(back_shelf)
                new_shelf_count += 1
                for level_num in range(1, shelf_cfg.num_levels + 1):
                    level = Level(id=uuid.uuid4(), shelf_id=back_shelf.id, level_number=level_num)
                    db.add(level)
                    for pos in range(1, shelf_cfg.num_locations + 1):
                        db.add(Location(id=uuid.uuid4(), level_id=level.id, position_number=pos))
                        new_location_count += 1
            db_aisle += 1

    warehouse.num_shelves = (warehouse.num_shelves or 0) + new_shelf_count
    warehouse.total_locations = (warehouse.total_locations or 0) + new_location_count

    await db.commit()
    await db.refresh(warehouse)
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    warehouse_data: WarehouseNameUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.company_id == current_user.company_id
        )
    )
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado")

    warehouse.name = warehouse_data.name

    await db.commit()
    await db.refresh(warehouse)
    return warehouse


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse(
    warehouse_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.company_id == current_user.company_id
        )
    )
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado")

    await db.delete(warehouse)
    await db.commit()
