from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Movement, InventoryItem, Location
from app.schemas.schemas import MovementCreate, MovementResponse
from app.api.deps import get_current_admin, get_current_user
from app.services.websocket_service import websocket_service
import uuid

router = APIRouter(prefix="/movements", tags=["movements"])

@router.get("", response_model=list[MovementResponse])
async def get_movements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Movement).where(Movement.company_id == current_user.company_id)
    )
    return result.scalars().all()


@router.get("/{movement_id}", response_model=MovementResponse)
async def get_movement(
    movement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Movement).where(
            Movement.id == movement_id,
            Movement.company_id == current_user.company_id
        )
    )
    movement = result.scalar_one_or_none()
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movimiento no encontrado")
    return movement


@router.get("/task/{task_id}", response_model=list[MovementResponse])
async def get_movements_by_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Movement).where(
            Movement.task_id == task_id,
            Movement.company_id == current_user.company_id
        )
    )
    return result.scalars().all()


@router.post("", response_model=MovementResponse, status_code=status.HTTP_201_CREATED)
async def create_movement(
    movement_data: MovementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if movement_data.type.value != "salida" and movement_data.product_id is None and movement_data.box_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El movimiento debe afectar a un producto o una caja"
        )

    if movement_data.type.value == "entrada":
        if movement_data.destination_location_id is None:
            raise HTTPException(status_code=400, detail="La entrada requiere ubicación de destino")
        existing = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == movement_data.destination_location_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="La ubicación de destino ya tiene inventario asignado")
        item = InventoryItem(
            id=uuid.uuid4(),
            location_id=movement_data.destination_location_id,
            product_id=movement_data.product_id,
            box_id=movement_data.box_id,
            quantity=1 if movement_data.product_id else None
        )
        db.add(item)

    elif movement_data.type.value == "salida":
        if movement_data.origin_location_id is None:
            raise HTTPException(status_code=400, detail="La salida requiere ubicación de origen")
        result = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == movement_data.origin_location_id)
        )
        item = result.scalar_one_or_none()
        if item:
            await db.delete(item)

    elif movement_data.type.value == "traslado":
        if movement_data.origin_location_id is None or movement_data.destination_location_id is None:
            raise HTTPException(status_code=400, detail="El traslado requiere ubicación de origen y destino")
        existing_dest = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == movement_data.destination_location_id)
        )
        if existing_dest.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="La ubicación de destino ya tiene inventario asignado")
        result = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == movement_data.origin_location_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=400, detail="No hay inventario en la ubicación de origen")
        item.location_id = movement_data.destination_location_id

    movement = Movement(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        task_id=movement_data.task_id,
        performed_by=current_user.id,
        type=movement_data.type,
        product_id=movement_data.product_id,
        box_id=movement_data.box_id,
        origin_location_id=movement_data.origin_location_id,
        destination_location_id=movement_data.destination_location_id
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)

    await websocket_service.broadcast_movement_created(
        movement_id=str(movement.id),
        data={
            "type": movement.type.value,
            "origin_location_id": str(movement.origin_location_id) if movement.origin_location_id else None,
            "destination_location_id": str(movement.destination_location_id) if movement.destination_location_id else None,
        }
    )

    return movement
