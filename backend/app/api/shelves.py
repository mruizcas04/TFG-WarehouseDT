from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Shelf, Level
from app.schemas.schemas import ShelfResponse, LevelResponse
from app.api.deps import get_current_admin
import uuid

router = APIRouter(tags=["shelves"])

@router.get("/warehouses/{warehouse_id}/shelves", response_model=list[ShelfResponse])
async def get_shelves(
    warehouse_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(select(Shelf).where(Shelf.warehouse_id == warehouse_id))
    return result.scalars().all()


@router.get("/shelves/{shelf_id}", response_model=ShelfResponse)
async def get_shelf(
    shelf_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(select(Shelf).where(Shelf.id == shelf_id))
    shelf = result.scalar_one_or_none()
    if not shelf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estantería no encontrada")
    return shelf


@router.get("/shelves/{shelf_id}/levels", response_model=list[LevelResponse])
async def get_levels(
    shelf_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(select(Level).where(Level.shelf_id == shelf_id))
    return result.scalars().all()


@router.get("/levels/{level_id}", response_model=LevelResponse)
async def get_level(
    level_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(select(Level).where(Level.id == level_id))
    level = result.scalar_one_or_none()
    if not level:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nivel no encontrado")
    return level