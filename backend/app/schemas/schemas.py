from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.models import UserRole, TaskType, TaskStatus, MovementType

# --- Auth ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: UUID
    role: UserRole
    company_id: UUID

# --- Company ---

class CompanyResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}

# --- User ---

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: Optional[str] = None
    role: UserRole
    company_name: Optional[str] = None

class UserResponse(BaseModel):
    id: UUID
    company_id: Optional[UUID]
    name: str
    email: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class UserCreateResponse(UserResponse):
    temporary_password: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# --- Warehouse ---

class ShelfConfig(BaseModel):
    num_levels: int
    num_locations: int

class AisleConfig(BaseModel):
    shelves: list[ShelfConfig]

class WarehouseCreate(BaseModel):
    name: str
    aisles: list[AisleConfig]

class WarehouseNameUpdate(BaseModel):
    name: str

class WarehouseResponse(BaseModel):
    id: UUID
    company_id: Optional[UUID]
    name: str
    num_shelves: int
    num_levels: Optional[int]
    num_locations: Optional[int]
    total_locations: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}

# --- Warehouse Full (para el Gemelo Digital) ---

class InventoryItemFullResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID]
    product_name: Optional[str] = None
    box_id: Optional[UUID]
    quantity: Optional[int]
    box_current_quantity: Optional[int] = None
    box_max_capacity: Optional[int] = None

    model_config = {"from_attributes": True}

class LocationFullResponse(BaseModel):
    id: UUID
    position_number: int
    nfc_tag: Optional[str]
    inventory: Optional[InventoryItemFullResponse] = None

    model_config = {"from_attributes": True}

class LevelFullResponse(BaseModel):
    id: UUID
    level_number: int
    locations: list[LocationFullResponse]

    model_config = {"from_attributes": True}

class ShelfFullResponse(BaseModel):
    id: UUID
    aisle_number: int
    shelf_number: int
    levels: list[LevelFullResponse]

    model_config = {"from_attributes": True}

class WarehouseFullResponse(BaseModel):
    id: UUID
    name: str
    num_shelves: int
    num_levels: Optional[int] = None
    num_locations: Optional[int] = None
    total_locations: Optional[int] = None
    created_at: datetime
    shelves: list[ShelfFullResponse]
    active_task_locations: list[str] = []
    active_task_info: dict[str, str] = {}

    model_config = {"from_attributes": True}

# --- Shelf ---

class ShelfResponse(BaseModel):
    id: UUID
    warehouse_id: UUID
    aisle_number: int
    shelf_number: int

    model_config = {"from_attributes": True}

# --- Level ---

class LevelResponse(BaseModel):
    id: UUID
    shelf_id: UUID
    level_number: int

    model_config = {"from_attributes": True}

# --- Location ---

class LocationResponse(BaseModel):
    id: UUID
    level_id: UUID
    position_number: int
    nfc_tag: Optional[str]

    model_config = {"from_attributes": True}

class LocationNFCUpdate(BaseModel):
    nfc_tag: str

# --- Category ---

class CategoryCreate(BaseModel):
    name: str
    color: str = "#888780"

class CategoryResponse(BaseModel):
    id: UUID
    company_id: Optional[UUID]
    name: str
    color: str

    model_config = {"from_attributes": True}

# --- Product ---

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    barcode: Optional[str] = None
    category_id: Optional[UUID] = None

class ProductResponse(BaseModel):
    id: UUID
    company_id: Optional[UUID]
    name: str
    description: Optional[str]
    type: Optional[str]
    barcode: Optional[str]
    category_id: Optional[UUID]
    category: Optional[CategoryResponse] = None
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}

# --- Box ---

class BoxCreate(BaseModel):
    product_id: UUID
    current_quantity: int
    max_capacity: int

class BoxResponse(BaseModel):
    id: UUID
    company_id: Optional[UUID]
    product_id: UUID
    current_quantity: int
    max_capacity: int

    model_config = {"from_attributes": True}

# --- InventoryItem ---

class InventoryItemResponse(BaseModel):
    id: UUID
    location_id: UUID
    product_id: Optional[UUID]
    box_id: Optional[UUID]
    quantity: Optional[int]

    model_config = {"from_attributes": True}

# --- Task ---

class TaskCreate(BaseModel):
    assigned_to: UUID
    type: TaskType
    product_id: Optional[UUID] = None
    quantity: Optional[int] = None
    origin_location_id: Optional[UUID] = None
    destination_location_id: Optional[UUID] = None

class TaskStatusUpdate(BaseModel):
    status: TaskStatus

class TaskResponse(BaseModel):
    id: UUID
    company_id: Optional[UUID]
    created_by: UUID
    assigned_to: UUID
    type: TaskType
    status: TaskStatus
    product_id: Optional[UUID]
    box_id: Optional[UUID]
    quantity: Optional[int]
    origin_location_id: Optional[UUID]
    destination_location_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}

# --- Inventory Summary ---

class ProductStockSummary(BaseModel):
    product_id: UUID
    product_name: str
    product_type: Optional[str]
    product_barcode: Optional[str]
    total_units: int
    locations_count: int
    pending_in: int
    pending_out: int

# --- Movement ---

class MovementCreate(BaseModel):
    task_id: UUID
    type: MovementType
    product_id: Optional[UUID] = None
    box_id: Optional[UUID] = None
    quantity: Optional[int] = None
    origin_location_id: Optional[UUID] = None
    destination_location_id: Optional[UUID] = None

class MovementResponse(BaseModel):
    id: UUID
    company_id: Optional[UUID]
    task_id: UUID
    performed_by: UUID
    type: MovementType
    product_id: Optional[UUID]
    box_id: Optional[UUID]
    quantity: Optional[int]
    origin_location_id: Optional[UUID]
    destination_location_id: Optional[UUID]
    timestamp: datetime

    model_config = {"from_attributes": True}
