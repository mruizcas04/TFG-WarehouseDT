from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.email import send_verification_email, send_temp_password_email, send_reset_password_email
from app.models.models import User, Company, UserRole
from app.schemas.schemas import (
    Token, UserCreate, UserResponse, UserCreateResponse, ChangePasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.api.deps import get_current_admin, get_current_user, get_user_from_token
from datetime import datetime, timedelta
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

    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debes verificar tu email antes de iniciar sesión. Revisa tu bandeja de entrada.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role.value,
        "company_id": str(user.company_id) if user.company_id else None,
        "must_change_password": user.must_change_password,
    })
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese email"
        )

    temporary_password = None

    if user_data.company_name is not None:
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
        must_change_password = False
        is_email_verified = False
        verification_token = secrets.token_urlsafe(32)
    else:
        try:
            token = await _extract_token(request)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Se requiere autenticación de administrador para añadir usuarios a una empresa"
            )
        current_admin = await get_user_from_token(token, db)
        company_id = current_admin.company_id
        company_result = await db.execute(select(Company).where(Company.id == company_id))
        company_name_for_email = company_result.scalar_one().name
        role = user_data.role
        temporary_password = secrets.token_urlsafe(10)
        password_to_hash = temporary_password
        must_change_password = True
        is_email_verified = True
        verification_token = None

    new_user = User(
        id=uuid.uuid4(),
        company_id=company_id,
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(password_to_hash),
        role=role,
        must_change_password=must_change_password,
        is_email_verified=is_email_verified,
        verification_token=verification_token,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    if verification_token:
        await send_verification_email(new_user.email, new_user.name, verification_token)

    if temporary_password:
        await send_temp_password_email(new_user.email, new_user.name, temporary_password, company_name_for_email)

    response = UserCreateResponse.model_validate(new_user)
    return response


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de verificación inválido o ya utilizado"
        )

    user.is_email_verified = True
    user.verification_token = None
    await db.commit()
    return {"message": "Email verificado correctamente. Ya puedes iniciar sesión."}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # Always return the same response to avoid revealing registered emails
    if user and user.is_active and user.is_email_verified:
        reset_token = secrets.token_urlsafe(32)
        user.reset_password_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(minutes=30)
        await db.commit()
        await send_reset_password_email(user.email, user.name, reset_token)

    return {"message": "Si el email está registrado, recibirás un enlace para restablecer tu contraseña."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.reset_password_token == data.token))
    user = result.scalar_one_or_none()

    if not user or user.reset_token_expires is None or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de recuperación no es válido o ha expirado"
        )

    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La contraseña debe tener al menos 8 caracteres"
        )

    user.password_hash = get_password_hash(data.new_password)
    user.reset_password_token = None
    user.reset_token_expires = None
    user.must_change_password = False
    await db.commit()
    return {"message": "Contraseña restablecida correctamente. Ya puedes iniciar sesión."}


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


@router.post("/change-password", response_model=Token)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta",
        )
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La nueva contraseña debe tener al menos 8 caracteres",
        )

    current_user.password_hash = get_password_hash(data.new_password)
    current_user.must_change_password = False
    await db.commit()

    access_token = create_access_token(data={
        "sub": str(current_user.id),
        "role": current_user.role.value,
        "company_id": str(current_user.company_id) if current_user.company_id else None,
        "must_change_password": False,
    })
    return {"access_token": access_token, "token_type": "bearer"}
