from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.models import User, Company, UserRole
from app.schemas.schemas import Token, UserCreate, UserResponse, UserCreateResponse
from app.api.deps import get_current_admin, get_current_user, get_user_from_token
import uuid
import secrets

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario desactivado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role.value,
        "company_id": str(user.company_id) if user.company_id else None,
    })
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Comprobar email duplicado
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese email"
        )

    temporary_password = None

    if user_data.company_name is not None:
        # Registro de empresa nueva: el usuario aporta su propia contraseña
        if not user_data.password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Se requiere contraseña al crear una nueva empresa"
            )
        company = Company(id=uuid.uuid4(), name=user_data.company_name)
        db.add(company)
        await db.flush()
        company_id = company.id
        role = UserRole.admin
        password_to_hash = user_data.password
    else:
        # Alta de usuario en empresa existente: requiere admin autenticado, contraseña generada automáticamente
        try:
            token = await _extract_token(request)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Se requiere autenticación de administrador para añadir usuarios a una empresa"
            )
        current_admin = await get_user_from_token(token, db)
        company_id = current_admin.company_id
        role = user_data.role
        temporary_password = secrets.token_urlsafe(10)
        password_to_hash = temporary_password

    new_user = User(
        id=uuid.uuid4(),
        company_id=company_id,
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(password_to_hash),
        role=role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    response = UserCreateResponse.model_validate(new_user)
    response.temporary_password = temporary_password
    return response


async def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    return auth_header[7:]


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
    show_inactive: bool = Query(False)
):
    active_filter = User.is_active == (False if show_inactive else True)
    result = await db.execute(
        select(User).where(
            User.company_id == current_user.company_id,
            active_filter
        )
    )
    return result.scalars().all()


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta"
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.company_id == current_user.company_id
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    user.is_active = False
    await db.commit()
