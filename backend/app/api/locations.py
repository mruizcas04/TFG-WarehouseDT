from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db.database import get_db
from app.models.models import User, Location, Level, Shelf, Warehouse, InventoryItem, Box, Product
from app.schemas.schemas import LocationResponse, LocationNFCUpdate, LocationInventorySetup
from app.api.deps import get_current_admin, get_current_user
from app.services.websocket_service import websocket_service
import uuid

router = APIRouter(tags=["locations"])

def _location_company_query(company_id: uuid.UUID):
    return (
        select(Location)
        .join(Level, Location.level_id == Level.id)
        .join(Shelf, Level.shelf_id == Shelf.id)
        .join(Warehouse, Shelf.warehouse_id == Warehouse.id)
        .where(Warehouse.company_id == company_id)
    )

@router.get("/levels/{level_id}/locations", response_model=list[LocationResponse])
async def get_locations(
    level_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        _location_company_query(current_user.company_id)
        .where(Location.level_id == level_id)
    )
    return result.scalars().all()


@router.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        _location_company_query(current_user.company_id)
        .where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada")
    return location


@router.get("/locations/nfc/{nfc_tag}", response_model=LocationResponse)
async def get_location_by_nfc(
    nfc_tag: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        _location_company_query(current_user.company_id)
        .where(Location.nfc_tag == nfc_tag)
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada")
    return location


@router.put("/locations/{location_id}/nfc", response_model=LocationResponse)
async def update_location_nfc(
    location_id: uuid.UUID,
    nfc_data: LocationNFCUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        _location_company_query(current_user.company_id)
        .where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada")

    location.nfc_tag = nfc_data.nfc_tag
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este tag NFC ya está asignado a otra ubicación"
        )
    await db.refresh(location)
    return location


@router.post("/locations/{location_id}/inventory", status_code=status.HTTP_201_CREATED)
async def setup_location_inventory(
    location_id: uuid.UUID,
    data: LocationInventorySetup,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        _location_company_query(current_user.company_id)
        .where(Location.id == location_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada")

    existing = await db.execute(
        select(InventoryItem).where(InventoryItem.location_id == location_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta ubicación ya tiene inventario")

    prod_result = await db.execute(
        select(Product).where(Product.id == data.product_id, Product.company_id == current_user.company_id)
    )
    if not prod_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    if data.quantity > 1:
        new_box = Box(
            id=uuid.uuid4(),
            company_id=current_user.company_id,
            product_id=data.product_id,
            current_quantity=data.quantity,
            max_capacity=data.quantity,
        )
        db.add(new_box)
        await db.flush()
        item = InventoryItem(
            id=uuid.uuid4(),
            location_id=location_id,
            product_id=None,
            box_id=new_box.id,
            quantity=None,
        )
    else:
        item = InventoryItem(
            id=uuid.uuid4(),
            location_id=location_id,
            product_id=data.product_id,
            box_id=None,
            quantity=1,
        )

    db.add(item)
    await db.commit()

    destination_inventory = {
        "id": str(item.id),
        "product_id": str(data.product_id) if data.quantity == 1 else None,
        "box_id": str(new_box.id) if data.quantity > 1 else None,
        "quantity": data.quantity,
    }
    await websocket_service.broadcast_movement_created(
        movement_id=str(uuid.uuid4()),
        data={
            "type": "entrada",
            "origin_location_id": None,
            "destination_location_id": str(location_id),
            "origin_state": "free",
            "destination_state": "box" if data.quantity > 1 else "product",
        },
        origin_inventory=None,
        destination_inventory=destination_inventory,
    )

    return {"success": True}
