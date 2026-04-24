from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Task
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
    result = await db.execute(select(Task))
    return result.scalars().all()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    task = Task(
        id=uuid.uuid4(),
        created_by=current_user.id,
        assigned_to=task_data.assigned_to,
        type=task_data.type,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await websocket_service.broadcast_task_assigned(
        task_id=str(task.id),
        assigned_to=str(task.assigned_to)
    )
    return task

@router.get("/user/{user_id}", response_model=list[TaskResponse])
async def get_tasks_by_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.assigned_to == user_id))
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return task


@router.put("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: uuid.UUID,
    status_data: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    task.status = status_data.status
    await db.commit()
    await db.refresh(task)
    await websocket_service.broadcast_task_status_changed(
        task_id=str(task.id),
        status=task.status.value
    )
    return task