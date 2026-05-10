from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, InventoryItem, Location, Level, Shelf, Warehouse
from app.schemas.schemas import InventoryItemResponse
from app.api.deps import get_current_user
import uuid

router = APIRouter(prefix="/inventory", tags=["inventory"])

def _inventory_company_query(company_id: uuid.UUID):
    return (
        select(InventoryItem)
        .join(Location, InventoryItem.location_id == Location.id)
        .join(Level, Location.level_id == Level.id)
        .join(Shelf, Level.shelf_id == Shelf.id)
        .join(Warehouse, Shelf.warehouse_id == Warehouse.id)
        .where(Warehouse.company_id == company_id)
    )

@router.get("", response_model=list[InventoryItemResponse])
async def get_inventory(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(_inventory_company_query(current_user.company_id))
    return result.scalars().all()


@router.get("/{item_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        _inventory_company_query(current_user.company_id)
        .where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")
    return item
