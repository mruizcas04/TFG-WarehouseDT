from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Movement, InventoryItem, Box, Product
from app.schemas.schemas import MovementCreate, MovementResponse
from app.api.deps import get_current_admin, get_current_user
from app.services.websocket_service import websocket_service
import uuid

router = APIRouter(prefix="/movements", tags=["movements"])

def _inventory_to_dict(item: InventoryItem | None, box: Box | None = None) -> dict | None:
    if item is None:
        return None
    effective_quantity = item.quantity if item.product_id else (box.current_quantity if box else None)
    return {
        "id": str(item.id),
        "product_id": str(item.product_id) if item.product_id else None,
        "box_id": str(item.box_id) if item.box_id else None,
        "quantity": effective_quantity,
        "box_current_quantity": box.current_quantity if box else None,
        "box_max_capacity": box.max_capacity if box else None,
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
    if movement_data.type.value != "salida" and movement_data.product_id is None and movement_data.box_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El movimiento debe afectar a un producto o una caja"
        )

    origin_inventory_dict = None
    destination_inventory_dict = None
    movement_box_id = movement_data.box_id  # puede quedar seteado al auto-crear caja

    if movement_data.type.value == "entrada":
        if movement_data.destination_location_id is None:
            raise HTTPException(status_code=400, detail="La entrada requiere ubicación de destino")

        existing_result = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == movement_data.destination_location_id)
        )
        existing_item = existing_result.scalar_one_or_none()

        quantity = movement_data.quantity or 1

        if existing_item:
            # Hay inventario existente — solo permitir si es el mismo producto y tiene units_per_location
            existing_product_id = existing_item.product_id
            existing_box = None
            if existing_item.box_id:
                box_result = await db.execute(select(Box).where(Box.id == existing_item.box_id))
                existing_box = box_result.scalar_one_or_none()
                if existing_box:
                    existing_product_id = existing_box.product_id

            if existing_product_id != movement_data.product_id:
                raise HTTPException(status_code=400, detail="La ubicación ya contiene un producto diferente")

            product_result = await db.execute(select(Product).where(Product.id == movement_data.product_id))
            product = product_result.scalar_one_or_none()

            if not product or product.units_per_location is None:
                raise HTTPException(status_code=400, detail="La ubicación ya tiene inventario asignado y el producto no permite acumulación")

            current_qty = existing_item.quantity if existing_item.product_id else (existing_box.current_quantity if existing_box else 0)

            if current_qty + quantity > product.units_per_location:
                raise HTTPException(
                    status_code=400,
                    detail=f"Capacidad máxima superada. Quedan {product.units_per_location - current_qty} hueco(s) disponibles en esta ubicación"
                )

            if existing_item.product_id:
                existing_item.quantity = current_qty + quantity
            elif existing_box:
                existing_box.current_quantity = current_qty + quantity
                if existing_box.max_capacity < existing_box.current_quantity:
                    existing_box.max_capacity = existing_box.current_quantity

            item = existing_item
            dest_box = existing_box
            destination_inventory_dict = _inventory_to_dict(item, dest_box)

        else:
            # No hay inventario existente — verificar capacidad antes de crear
            if movement_data.product_id:
                product_result = await db.execute(select(Product).where(Product.id == movement_data.product_id))
                product = product_result.scalar_one_or_none()
                if product and product.units_per_location is not None and quantity > product.units_per_location:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Capacidad máxima superada. Esta ubicación admite como máximo {product.units_per_location} ud."
                    )

            if movement_data.product_id and quantity > 1:
                # Auto-crear caja: varios productos del mismo tipo se almacenan en caja
                new_box = Box(
                    id=uuid.uuid4(),
                    company_id=current_user.company_id,
                    product_id=movement_data.product_id,
                    current_quantity=quantity,
                    max_capacity=quantity,
                )
                db.add(new_box)
                await db.flush()
                movement_box_id = new_box.id
                item = InventoryItem(
                    id=uuid.uuid4(),
                    location_id=movement_data.destination_location_id,
                    product_id=None,
                    box_id=new_box.id,
                    quantity=None,
                )
                dest_box = new_box
            else:
                # Producto suelto (quantity == 1 o se entra directamente con box_id)
                item = InventoryItem(
                    id=uuid.uuid4(),
                    location_id=movement_data.destination_location_id,
                    product_id=movement_data.product_id,
                    box_id=movement_data.box_id,
                    quantity=quantity if movement_data.product_id else None,
                )
                dest_box = None
                if movement_data.box_id:
                    box_result = await db.execute(select(Box).where(Box.id == movement_data.box_id))
                    dest_box = box_result.scalar_one_or_none()
            db.add(item)
            destination_inventory_dict = _inventory_to_dict(item, dest_box)

    elif movement_data.type.value == "salida":
        if movement_data.origin_location_id is None:
            raise HTTPException(status_code=400, detail="La salida requiere ubicación de origen")
        result = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == movement_data.origin_location_id)
        )
        item = result.scalar_one_or_none()

        if item and item.box_id:
            # Salida desde una ubicación con caja
            box_result = await db.execute(select(Box).where(Box.id == item.box_id))
            box = box_result.scalar_one_or_none()
            movement_box_id = item.box_id
            quantity_out = movement_data.quantity or (box.current_quantity if box else 0)

            if box and quantity_out < box.current_quantity:
                # Salida parcial: la caja sigue, se reduce cantidad
                box.current_quantity -= quantity_out
                origin_inventory_dict = _inventory_to_dict(item, box)
            else:
                # Salida total: se elimina el InventoryItem
                await db.delete(item)
                origin_inventory_dict = None
        elif item:
            # Salida de producto suelto
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
        if item.box_id:
            movement_box_id = item.box_id
        item.location_id = movement_data.destination_location_id

        dest_box = None
        if item.box_id:
            box_result = await db.execute(select(Box).where(Box.id == item.box_id))
            dest_box = box_result.scalar_one_or_none()
        destination_inventory_dict = _inventory_to_dict(item, dest_box)
        origin_inventory_dict = None

    movement = Movement(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        task_id=movement_data.task_id,
        performed_by=current_user.id,
        type=movement_data.type,
        product_id=movement_data.product_id,
        box_id=movement_box_id,
        quantity=movement_data.quantity,
        origin_location_id=movement_data.origin_location_id,
        destination_location_id=movement_data.destination_location_id
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)

    def _state_from_dict(d: dict | None) -> str:
        if d is None:
            return "free"
        if d.get("box_id"):
            return "box"
        if d.get("product_id"):
            return "product"
        return "free"

    await websocket_service.broadcast_movement_created(
        movement_id=str(movement.id),
        data={
            "type": movement.type.value,
            "origin_location_id": str(movement.origin_location_id) if movement.origin_location_id else None,
            "destination_location_id": str(movement.destination_location_id) if movement.destination_location_id else None,
            "origin_state": _state_from_dict(origin_inventory_dict),
            "destination_state": _state_from_dict(destination_inventory_dict),
        },
        origin_inventory=origin_inventory_dict,
        destination_inventory=destination_inventory_dict,
    )

    return movement
