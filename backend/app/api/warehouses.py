from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.database import get_db
from app.models.models import User, Warehouse, Shelf, Level, Location, InventoryItem
from app.schemas.schemas import WarehouseCreate, WarehouseResponse, WarehouseFullResponse
from app.api.deps import get_current_admin, get_current_user
import uuid

router = APIRouter(prefix="/warehouses", tags=["warehouses"])

@router.get("", response_model=list[WarehouseResponse])
async def get_warehouses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(select(Warehouse))
    return result.scalars().all()


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    warehouse = Warehouse(
        id=uuid.uuid4(),
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
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
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
    """
    Devuelve la estructura completa del almacén con todas las estanterías,
    niveles, ubicaciones y su estado de inventario actual.
    Usado por el Gemelo Digital Unity para inicializarse.
    """
    result = await db.execute(
        select(Warehouse)
        .where(Warehouse.id == warehouse_id)
        .options(
            selectinload(Warehouse.shelves)
            .selectinload(Shelf.levels)
            .selectinload(Level.locations)
            .selectinload(Location.inventory_item)
        )
    )
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado")
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    warehouse_data: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
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
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado")

    await db.delete(warehouse)
    await db.commit()