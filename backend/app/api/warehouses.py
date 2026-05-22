from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Warehouse, Shelf, Level, Location, InventoryItem, Box, Product, Task, TaskStatus
from app.schemas.schemas import (
    WarehouseCreate, WarehouseNameUpdate, WarehouseResponse, WarehouseFullResponse,
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

    box_ids = [item.box_id for item in inventory_items if item.box_id]
    boxes_by_id = {}
    if box_ids:
        boxes_result = await db.execute(select(Box).where(Box.id.in_(box_ids)))
        boxes_by_id = {box.id: box for box in boxes_result.scalars().all()}

    direct_product_ids = [item.product_id for item in inventory_items if item.product_id]
    box_product_ids = [box.product_id for box in boxes_by_id.values() if box.product_id]
    all_product_ids = list(set(direct_product_ids + box_product_ids))
    products_by_id = {}
    if all_product_ids:
        products_result = await db.execute(select(Product).where(Product.id.in_(all_product_ids)))
        products_by_id = {p.id: p for p in products_result.scalars().all()}

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
                    box = boxes_by_id.get(inv.box_id) if inv.box_id else None
                    effective_product_id = inv.product_id or (box.product_id if box else None)
                    product = products_by_id.get(effective_product_id) if effective_product_id else None
                    effective_quantity = inv.quantity if inv.product_id else (box.current_quantity if box else None)
                    inventory_dto = InventoryItemFullResponse(
                        id=inv.id,
                        product_id=inv.product_id,
                        product_name=product.name if product else None,
                        box_id=inv.box_id,
                        quantity=effective_quantity,
                        box_current_quantity=box.current_quantity if box else None,
                        box_max_capacity=box.max_capacity if box else None,
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
