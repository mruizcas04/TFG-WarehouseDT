from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Movement, InventoryItem, Product
from app.schemas.schemas import MovementCreate, MovementResponse
from app.api.deps import get_current_admin, get_current_user
from app.services.websocket_service import websocket_service
import uuid

router = APIRouter(prefix="/movements", tags=["movements"])

def _inventory_to_dict(item: InventoryItem | None) -> dict | None:
    if item is None:
        return None
    return {
        "id": str(item.id),
        "product_id": str(item.product_id),
        "quantity": item.quantity,
    }


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
    if movement_data.product_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El movimiento debe especificar un producto"
        )

    origin_inventory_dict = None
    destination_inventory_dict = None

    if movement_data.type.value == "entrada":
        if movement_data.destination_location_id is None:
            raise HTTPException(status_code=400, detail="La entrada requiere ubicación de destino")

        existing_result = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == movement_data.destination_location_id)
        )
        existing_item = existing_result.scalar_one_or_none()
        quantity = movement_data.quantity or 1

        if existing_item:
            if existing_item.product_id != movement_data.product_id:
                raise HTTPException(status_code=400, detail="La ubicación ya contiene un producto diferente")

            product_result = await db.execute(select(Product).where(Product.id == movement_data.product_id))
            product = product_result.scalar_one_or_none()

            if not product or product.units_per_location is None:
                raise HTTPException(status_code=400, detail="La ubicación ya tiene inventario asignado y el producto no permite acumulación")

            if existing_item.quantity + quantity > product.units_per_location:
                raise HTTPException(
                    status_code=400,
                    detail=f"Capacidad máxima superada. Quedan {product.units_per_location - existing_item.quantity} hueco(s) disponibles en esta ubicación"
                )

            existing_item.quantity += quantity
            destination_inventory_dict = _inventory_to_dict(existing_item)

        else:
            if movement_data.product_id:
                product_result = await db.execute(select(Product).where(Product.id == movement_data.product_id))
                product = product_result.scalar_one_or_none()
                if product and product.units_per_location is not None and quantity > product.units_per_location:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Capacidad máxima superada. Esta ubicación admite como máximo {product.units_per_location} ud."
                    )

            item = InventoryItem(
                id=uuid.uuid4(),
                location_id=movement_data.destination_location_id,
                product_id=movement_data.product_id,
                quantity=quantity,
            )
            db.add(item)
            destination_inventory_dict = _inventory_to_dict(item)

    elif movement_data.type.value == "salida":
        if movement_data.origin_location_id is None:
            raise HTTPException(status_code=400, detail="La salida requiere ubicación de origen")

        result = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == movement_data.origin_location_id)
        )
        item = result.scalar_one_or_none()

        if item:
            quantity_out = movement_data.quantity or item.quantity
            if quantity_out < item.quantity:
                item.quantity -= quantity_out
                origin_inventory_dict = _inventory_to_dict(item)
            else:
                await db.delete(item)
                origin_inventory_dict = None

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
        destination_inventory_dict = _inventory_to_dict(item)
        origin_inventory_dict = None

    movement = Movement(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        task_id=movement_data.task_id,
        performed_by=current_user.id,
        type=movement_data.type,
        product_id=movement_data.product_id,
        quantity=movement_data.quantity,
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
            "origin_state": "free" if origin_inventory_dict is None else "product",
            "destination_state": "free" if destination_inventory_dict is None else "product",
        },
        origin_inventory=origin_inventory_dict,
        destination_inventory=destination_inventory_dict,
    )

    return movement
