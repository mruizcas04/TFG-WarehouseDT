from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.models.models import User, InventoryItem, Location, Level, Shelf, Warehouse, Task, TaskStatus, TaskType, Product
from app.schemas.schemas import InventoryItemResponse, ProductStockSummary
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

@router.get("/summary", response_model=list[ProductStockSummary])
async def get_inventory_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company_id = current_user.company_id

    stock_sq = (
        select(
            InventoryItem.product_id,
            func.coalesce(func.sum(InventoryItem.quantity), 0).label("total_units"),
            func.count(InventoryItem.id).label("locations_count"),
        )
        .join(Location, InventoryItem.location_id == Location.id)
        .join(Level, Location.level_id == Level.id)
        .join(Shelf, Level.shelf_id == Shelf.id)
        .join(Warehouse, Shelf.warehouse_id == Warehouse.id)
        .where(Warehouse.company_id == company_id)
        .group_by(InventoryItem.product_id)
        .subquery()
    )

    pending_in_sq = (
        select(
            Task.product_id,
            func.sum(func.coalesce(Task.quantity, 1)).label("pending_in"),
        )
        .where(
            Task.company_id == company_id,
            Task.type == TaskType.entrada,
            Task.status.in_([TaskStatus.pendiente, TaskStatus.en_curso]),
            Task.product_id.isnot(None),
        )
        .group_by(Task.product_id)
        .subquery()
    )

    pending_out_sq = (
        select(
            Task.product_id,
            func.sum(func.coalesce(Task.quantity, 1)).label("pending_out"),
        )
        .where(
            Task.company_id == company_id,
            Task.type == TaskType.salida,
            Task.status.in_([TaskStatus.pendiente, TaskStatus.en_curso]),
            Task.product_id.isnot(None),
        )
        .group_by(Task.product_id)
        .subquery()
    )

    stmt = (
        select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.type.label("product_type"),
            Product.barcode.label("product_barcode"),
            func.coalesce(stock_sq.c.total_units, 0).label("total_units"),
            func.coalesce(stock_sq.c.locations_count, 0).label("locations_count"),
            func.coalesce(pending_in_sq.c.pending_in, 0).label("pending_in"),
            func.coalesce(pending_out_sq.c.pending_out, 0).label("pending_out"),
        )
        .outerjoin(stock_sq, Product.id == stock_sq.c.product_id)
        .outerjoin(pending_in_sq, Product.id == pending_in_sq.c.product_id)
        .outerjoin(pending_out_sq, Product.id == pending_out_sq.c.product_id)
        .where(Product.company_id == company_id)
        .order_by(func.coalesce(stock_sq.c.total_units, 0).desc())
    )

    result = await db.execute(stmt)
    rows = result.mappings().all()

    return [
        ProductStockSummary(
            product_id=row["product_id"],
            product_name=row["product_name"],
            product_type=row["product_type"],
            product_barcode=row["product_barcode"],
            total_units=row["total_units"],
            locations_count=row["locations_count"],
            pending_in=row["pending_in"],
            pending_out=row["pending_out"],
        )
        for row in rows
    ]


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
