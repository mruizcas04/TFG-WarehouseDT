from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Warehouse, Shelf, Level, Location, InventoryItem
from app.schemas.schemas import (
    WarehouseCreate, WarehouseResponse, WarehouseFullResponse,
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
    warehouse = Warehouse(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        name=warehouse_data.name,
        num_shelves=warehouse_data.num_shelves,
        num_levels=warehouse_data.num_levels,
        num_locations=warehouse_data.num_locations
    )
    db.add(warehouse)

    for aisle in range(1, warehouse_data.num_shelves + 1):
        shelf = Shelf(
            id=uuid.uuid4(),
            warehouse_id=warehouse.id,
            aisle_number=aisle,
            shelf_number=1
        )
        db.add(shelf)

        for level_num in range(1, warehouse_data.num_levels + 1):
            level = Level(
                id=uuid.uuid4(),
                shelf_id=shelf.id,
                level_number=level_num
            )
            db.add(level)

            for pos in range(1, warehouse_data.num_locations + 1):
                location = Location(
                    id=uuid.uuid4(),
                    level_id=level.id,
                    position_number=pos
                )
                db.add(location)

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
                inventory_dto = InventoryItemFullResponse(
                    id=inv.id,
                    product_id=inv.product_id,
                    box_id=inv.box_id,
                    quantity=inv.quantity
                ) if inv else None

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
            levels=levels_full
        ))

    return WarehouseFullResponse(
        id=warehouse.id,
        name=warehouse.name,
        num_shelves=warehouse.num_shelves,
        num_levels=warehouse.num_levels,
        num_locations=warehouse.num_locations,
        created_at=warehouse.created_at,
        shelves=shelves_full
    )


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    warehouse_data: WarehouseCreate,
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
    warehouse.num_shelves = warehouse_data.num_shelves
    warehouse.num_levels = warehouse_data.num_levels
    warehouse.num_locations = warehouse_data.num_locations

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
