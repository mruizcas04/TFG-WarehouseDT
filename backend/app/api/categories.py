from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Category
from app.schemas.schemas import CategoryCreate, CategoryResponse
from app.api.deps import get_current_admin, get_current_user
import uuid

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Category).where(Category.company_id == current_user.company_id).order_by(Category.name)
    )
    return result.scalars().all()


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    category = Category(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        name=category_data.name,
        color=category_data.color,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category
