from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Location
from app.schemas.schemas import LocationResponse, LocationNFCUpdate
from app.api.deps import get_current_admin, get_current_user
import uuid

router = APIRouter(tags=["locations"])

@router.get("/levels/{level_id}/locations", response_model=list[LocationResponse])
async def get_locations(
    level_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Location).where(Location.level_id == level_id))
    return result.scalars().all()


@router.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Location).where(Location.id == location_id))
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
    result = await db.execute(select(Location).where(Location.nfc_tag == nfc_tag))
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
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada")

    location.nfc_tag = nfc_data.nfc_tag
    await db.commit()
    await db.refresh(location)
    return location