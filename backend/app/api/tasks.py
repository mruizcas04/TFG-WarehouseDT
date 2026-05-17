from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Task, InventoryItem, Box, TaskStatus
from app.schemas.schemas import TaskCreate, TaskResponse, TaskStatusUpdate
from app.api.deps import get_current_admin, get_current_user
from app.services.websocket_service import websocket_service
import uuid

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("", response_model=list[TaskResponse])
async def get_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Task).where(Task.company_id == current_user.company_id)
    )
    return result.scalars().all()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(User).where(
            User.id == task_data.assigned_to,
            User.company_id == current_user.company_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario asignado no pertenece a esta empresa"
        )

    # Validación de ubicaciones según tipo
    if task_data.type.value == "traslado":
        if not task_data.origin_location_id or not task_data.destination_location_id:
            raise HTTPException(status_code=400, detail="Las tareas de traslado requieren ubicación de origen y destino")
    elif task_data.type.value == "entrada" and not task_data.destination_location_id:
        raise HTTPException(status_code=400, detail="Las tareas de entrada requieren ubicación de destino")
    elif task_data.type.value == "salida" and not task_data.origin_location_id:
        raise HTTPException(status_code=400, detail="Las tareas de salida requieren ubicación de origen")

    # Destino debe estar vacío (entrada / traslado)
    if task_data.type.value in ("entrada", "traslado"):
        dest_inv = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == task_data.destination_location_id)
        )
        if dest_inv.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="La ubicación de destino ya tiene inventario asignado")

    # Origen debe tener el producto (salida / traslado)
    if task_data.type.value in ("salida", "traslado"):
        if not task_data.product_id:
            raise HTTPException(status_code=400, detail="Las tareas de salida y traslado requieren especificar un producto")

        origin_inv_result = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == task_data.origin_location_id)
        )
        origin_inv = origin_inv_result.scalar_one_or_none()

        if not origin_inv:
            raise HTTPException(status_code=400, detail="No hay inventario en la ubicación de origen")

        # El producto puede estar suelto o dentro de una caja
        origin_box = None
        if origin_inv.box_id:
            box_result = await db.execute(select(Box).where(Box.id == origin_inv.box_id))
            origin_box = box_result.scalar_one_or_none()

        product_matches = (
            origin_inv.product_id == task_data.product_id or
            (origin_box is not None and origin_box.product_id == task_data.product_id)
        )
        if not product_matches:
            raise HTTPException(status_code=400, detail="El producto seleccionado no se encuentra en la ubicación de origen")

        # Validar que la cantidad no supere el contenido de la caja
        if task_data.quantity and origin_box:
            if task_data.quantity > origin_box.current_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"La cantidad solicitada ({task_data.quantity}) supera el contenido de la caja ({origin_box.current_quantity} ud.)"
                )

    active_statuses = [TaskStatus.pendiente, TaskStatus.en_curso]

    if task_data.destination_location_id:
        conflict = await db.execute(
            select(Task).where(
                Task.destination_location_id == task_data.destination_location_id,
                Task.status.in_(active_statuses),
                Task.company_id == current_user.company_id,
            )
        )
        if conflict.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="La ubicación de destino ya tiene una tarea activa asignada")

    if task_data.origin_location_id:
        conflict = await db.execute(
            select(Task).where(
                Task.origin_location_id == task_data.origin_location_id,
                Task.status.in_(active_statuses),
                Task.company_id == current_user.company_id,
            )
        )
        if conflict.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="La ubicación de origen ya tiene una tarea activa asignada")

    task = Task(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        created_by=current_user.id,
        assigned_to=task_data.assigned_to,
        type=task_data.type,
        product_id=task_data.product_id,
        quantity=task_data.quantity,
        origin_location_id=task_data.origin_location_id,
        destination_location_id=task_data.destination_location_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await websocket_service.broadcast_task_assigned(
        task_id=str(task.id),
        assigned_to=str(task.assigned_to),
        origin_location_id=str(task.origin_location_id) if task.origin_location_id else None,
        destination_location_id=str(task.destination_location_id) if task.destination_location_id else None,
    )
    return task

@router.get("/user/{user_id}", response_model=list[TaskResponse])
async def get_tasks_by_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Task).where(
            Task.assigned_to == user_id,
            Task.company_id == current_user.company_id
        )
    )
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.company_id == current_user.company_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task


@router.put("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: uuid.UUID,
    status_data: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.company_id == current_user.company_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    task.status = status_data.status
    await db.commit()
    await db.refresh(task)
    await websocket_service.broadcast_task_status_changed(
        task_id=str(task.id),
        status=task.status.value,
        origin_location_id=str(task.origin_location_id) if task.origin_location_id else None,
        destination_location_id=str(task.destination_location_id) if task.destination_location_id else None,
    )
    return task
