from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Box
from app.schemas.schemas import BoxCreate, BoxResponse
from app.api.deps import get_current_admin, get_current_user
import uuid

router = APIRouter(prefix="/boxes", tags=["boxes"])

@router.get("", response_model=list[BoxResponse])
async def get_boxes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(select(Box))
    return result.scalars().all()


@router.post("", response_model=BoxResponse, status_code=status.HTTP_201_CREATED)
async def create_box(
    box_data: BoxCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    box = Box(
        id=uuid.uuid4(),
        product_id=box_data.product_id,
        current_quantity=box_data.current_quantity,
        max_capacity=box_data.max_capacity
    )
    db.add(box)
    await db.commit()
    await db.refresh(box)
    return box


@router.get("/{box_id}", response_model=BoxResponse)
async def get_box(
    box_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Box).where(Box.id == box_id))
    box = result.scalar_one_or_none()
    if not box:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")
    return box


@router.put("/{box_id}", response_model=BoxResponse)
async def update_box(
    box_id: uuid.UUID,
    box_data: BoxCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(select(Box).where(Box.id == box_id))
    box = result.scalar_one_or_none()
    if not box:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    box.product_id = box_data.product_id
    box.current_quantity = box_data.current_quantity
    box.max_capacity = box_data.max_capacity

    await db.commit()
    await db.refresh(box)
    return box