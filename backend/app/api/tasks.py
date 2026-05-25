from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete, func
from app.db.database import get_db
from app.models.models import User, Task, InventoryItem, Box, TaskStatus, Movement, Product, UserRole
from app.schemas.schemas import (
    TaskCreate, TaskResponse, TaskStatusUpdate,
    WorkerRecommendation, WorkerStats, StatsResponse,
)
from app.api.deps import get_current_admin, get_current_user
from app.services.websocket_service import websocket_service
from datetime import datetime, timedelta, date as date_type
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

    # Destino debe estar vacío para traslados; para entradas permite acumulación si el producto lo admite
    if task_data.type.value == "entrada":
        dest_inv_result = await db.execute(
            select(InventoryItem).where(InventoryItem.location_id == task_data.destination_location_id)
        )
        dest_inv = dest_inv_result.scalar_one_or_none()
        if dest_inv:
            dest_product_id = dest_inv.product_id
            dest_box = None
            if dest_inv.box_id:
                box_r = await db.execute(select(Box).where(Box.id == dest_inv.box_id))
                dest_box = box_r.scalar_one_or_none()
                if dest_box:
                    dest_product_id = dest_box.product_id

            if dest_product_id != task_data.product_id:
                raise HTTPException(status_code=400, detail="La ubicación de destino ya contiene un producto diferente")

            prod_r = await db.execute(select(Product).where(Product.id == task_data.product_id))
            prod = prod_r.scalar_one_or_none()
            if not prod or prod.units_per_location is None:
                raise HTTPException(status_code=400, detail="La ubicación de destino ya tiene inventario y el producto no permite acumulación")

            current_qty = dest_inv.quantity if dest_inv.product_id else (dest_box.current_quantity if dest_box else 0)
            incoming_qty = task_data.quantity or 1
            if current_qty + incoming_qty > prod.units_per_location:
                raise HTTPException(
                    status_code=400,
                    detail=f"La cantidad solicitada supera la capacidad máxima de la ubicación ({prod.units_per_location - current_qty} ud. disponibles)"
                )
        elif task_data.product_id:
            # Ubicación vacía — verificar igualmente que la cantidad no supera units_per_location
            prod_r = await db.execute(select(Product).where(Product.id == task_data.product_id))
            prod = prod_r.scalar_one_or_none()
            if prod and prod.units_per_location is not None:
                incoming_qty = task_data.quantity or 1
                if incoming_qty > prod.units_per_location:
                    raise HTTPException(
                        status_code=400,
                        detail=f"La cantidad solicitada supera la capacidad máxima de este producto por ubicación ({prod.units_per_location} ud.)"
                    )

    if task_data.type.value == "traslado":
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


@router.get("/recommendation", response_model=list[WorkerRecommendation])
async def get_worker_recommendation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    today_start = datetime.combine(date_type.today(), datetime.min.time())

    # Todos los workers activos de la empresa
    workers_result = await db.execute(
        select(User).where(
            User.company_id == current_user.company_id,
            User.role == UserRole.worker,
            User.is_active == True,
        )
    )
    all_workers = workers_result.scalars().all()

    if not all_workers:
        return []

    # Priorizar workers que están conectados ahora mismo
    online_workers = [w for w in all_workers if w.is_online]
    workers_to_rank = online_workers if online_workers else all_workers
    online_ids = {w.id for w in online_workers}

    recommendations = []
    for worker in workers_to_rank:
        pending_today = (await db.execute(
            select(func.count(Task.id)).where(
                Task.assigned_to == worker.id,
                Task.company_id == current_user.company_id,
                Task.status.in_([TaskStatus.pendiente, TaskStatus.en_curso]),
                Task.created_at >= today_start,
            )
        )).scalar() or 0

        pending_old = (await db.execute(
            select(func.count(Task.id)).where(
                Task.assigned_to == worker.id,
                Task.company_id == current_user.company_id,
                Task.status.in_([TaskStatus.pendiente, TaskStatus.en_curso]),
                Task.created_at < today_start,
            )
        )).scalar() or 0

        total_completed = (await db.execute(
            select(func.count(Task.id)).where(
                Task.assigned_to == worker.id,
                Task.company_id == current_user.company_id,
                Task.status == TaskStatus.completada,
            )
        )).scalar() or 0

        accumulation_rate = (pending_today + pending_old) / (total_completed + 1)
        score = pending_today * 0.5 + pending_old * 0.3 + accumulation_rate * 0.2

        recommendations.append({
            "user_id": worker.id,
            "name": worker.name,
            "score": score,
            "pending_today": pending_today,
            "pending_old": pending_old,
            "total_completed": total_completed,
            "is_active_today": worker.id in online_ids,
            "is_recommended": False,
        })

    recommendations.sort(key=lambda x: x["score"])
    if recommendations:
        recommendations[0]["is_recommended"] = True

    return recommendations


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    today = date_type.today()
    today_start = datetime.combine(today, datetime.min.time())
    week_start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    month_start = datetime.combine(today.replace(day=1), datetime.min.time())

    workers_result = await db.execute(
        select(User).where(
            User.company_id == current_user.company_id,
            User.role == UserRole.worker,
            User.is_active == True,
        )
    )
    workers = workers_result.scalars().all()

    worker_stats_list = []
    for worker in workers:
        total_assigned = (await db.execute(
            select(func.count(Task.id)).where(
                Task.assigned_to == worker.id,
                Task.company_id == current_user.company_id,
            )
        )).scalar() or 0

        total_completed = (await db.execute(
            select(func.count(Task.id)).where(
                Task.assigned_to == worker.id,
                Task.company_id == current_user.company_id,
                Task.status == TaskStatus.completada,
            )
        )).scalar() or 0

        total_pending = (await db.execute(
            select(func.count(Task.id)).where(
                Task.assigned_to == worker.id,
                Task.company_id == current_user.company_id,
                Task.status.in_([TaskStatus.pendiente, TaskStatus.en_curso]),
            )
        )).scalar() or 0

        pending_old = (await db.execute(
            select(func.count(Task.id)).where(
                Task.assigned_to == worker.id,
                Task.company_id == current_user.company_id,
                Task.status.in_([TaskStatus.pendiente, TaskStatus.en_curso]),
                Task.created_at < today_start,
            )
        )).scalar() or 0

        completed_this_week = (await db.execute(
            select(func.count(Task.id)).where(
                Task.assigned_to == worker.id,
                Task.company_id == current_user.company_id,
                Task.status == TaskStatus.completada,
                Task.completed_at >= week_start,
            )
        )).scalar() or 0

        completed_this_month = (await db.execute(
            select(func.count(Task.id)).where(
                Task.assigned_to == worker.id,
                Task.company_id == current_user.company_id,
                Task.status == TaskStatus.completada,
                Task.completed_at >= month_start,
            )
        )).scalar() or 0

        completion_rate = (total_completed / total_assigned * 100) if total_assigned > 0 else 0.0

        worker_stats_list.append(WorkerStats(
            user_id=worker.id,
            name=worker.name,
            total_assigned=total_assigned,
            total_completed=total_completed,
            total_pending=total_pending,
            completion_rate=completion_rate,
            pending_old=pending_old,
            completed_this_week=completed_this_week,
            completed_this_month=completed_this_month,
        ))

    # Métricas globales
    global_total_movements = (await db.execute(
        select(func.count(Movement.id)).where(Movement.company_id == current_user.company_id)
    )).scalar() or 0

    global_total_tasks_completed = (await db.execute(
        select(func.count(Task.id)).where(
            Task.company_id == current_user.company_id,
            Task.status == TaskStatus.completada,
        )
    )).scalar() or 0

    global_total_tasks = (await db.execute(
        select(func.count(Task.id)).where(Task.company_id == current_user.company_id)
    )).scalar() or 0

    global_completion_rate = (
        global_total_tasks_completed / global_total_tasks * 100
        if global_total_tasks > 0 else 0.0
    )

    # Día más activo de la semana
    timestamps_result = await db.execute(
        select(Movement.timestamp).where(Movement.company_id == current_user.company_id)
    )
    timestamps = timestamps_result.scalars().all()
    day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    day_counts: dict[str, int] = {}
    for ts in timestamps:
        day = day_names[ts.weekday()]
        day_counts[day] = day_counts.get(day, 0) + 1
    busiest_day = max(day_counts, key=day_counts.get) if day_counts else None

    # Worker más activo
    most_active_worker = None
    if worker_stats_list:
        best = max(worker_stats_list, key=lambda w: w.total_completed)
        if best.total_completed > 0:
            most_active_worker = best.name

    return StatsResponse(
        workers=worker_stats_list,
        global_total_movements=global_total_movements,
        global_total_tasks_completed=global_total_tasks_completed,
        global_completion_rate=global_completion_rate,
        busiest_day=busiest_day,
        most_active_worker=most_active_worker,
    )


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


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
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
    if task.status == TaskStatus.en_curso:
        raise HTTPException(status_code=400, detail="No se puede eliminar una tarea en curso")
    await db.execute(sql_delete(Movement).where(Movement.task_id == task_id))
    await db.delete(task)
    await db.commit()


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
    if status_data.status == TaskStatus.completada:
        task.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)
    await websocket_service.broadcast_task_status_changed(
        task_id=str(task.id),
        status=task.status.value,
        origin_location_id=str(task.origin_location_id) if task.origin_location_id else None,
        destination_location_id=str(task.destination_location_id) if task.destination_location_id else None,
    )
    return task
