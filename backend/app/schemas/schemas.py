from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional, Any
from uuid import UUID
from datetime import datetime
from app.models.models import UserRole, TaskType, TaskStatus, MovementType

# --- Auth ---

class Token(BaseModel):
    access_token: str
    token_type: str

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
    is_online: bool
    must_change_password: bool
    last_login: Optional[datetime] = None
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
    is_double: bool = False

class AisleConfig(BaseModel):
    shelves: list[ShelfConfig]

class WarehouseCreate(BaseModel):
    name: str
    aisles: list[AisleConfig]

class WarehouseNameUpdate(BaseModel):
    name: str

class ExtendAisleConfig(BaseModel):
    aisle_number: int
    new_shelves: list[ShelfConfig]

class WarehouseExpand(BaseModel):
    new_aisles: list[AisleConfig] = []
    extend_aisles: list[ExtendAisleConfig] = []

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
    product_id: UUID
    product_name: Optional[str] = None
    product_barcode: Optional[str] = None
    product_category: Optional[str] = None
    product_category_color: Optional[str] = None
    quantity: int

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
    is_double: bool = False
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
    is_double: bool = False

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
    aisle_number: Optional[int] = None
    shelf_number: Optional[int] = None
    level_number: Optional[int] = None

    model_config = {"from_attributes": True}

    @model_validator(mode='before')
    @classmethod
    def extract_hierarchy(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            return obj
        level = getattr(obj, 'level', None)
        shelf = getattr(level, 'shelf', None) if level else None
        return {
            'id': obj.id,
            'level_id': obj.level_id,
            'position_number': obj.position_number,
            'nfc_tag': obj.nfc_tag,
            'level_number': level.level_number if level else None,
            'shelf_number': shelf.shelf_number if shelf else None,
            'aisle_number': shelf.aisle_number if shelf else None,
        }

class LocationNFCUpdate(BaseModel):
    nfc_tag: str

class LocationInventorySetup(BaseModel):
    product_id: UUID
    quantity: int

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
    units_per_location: Optional[int] = None

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
    units_per_location: Optional[int] = None

    model_config = {"from_attributes": True}

# --- InventoryItem ---

class InventoryItemResponse(BaseModel):
    id: UUID
    location_id: UUID
    product_id: UUID
    quantity: int

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
    quantity: Optional[int]
    origin_location_id: Optional[UUID]
    destination_location_id: Optional[UUID]
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Worker Recommendation / Stats ---

class WorkerRecommendation(BaseModel):
    user_id: UUID
    name: str
    score: float
    pending_today: int
    pending_old: int
    total_completed: int
    is_active_today: bool
    is_recommended: bool


class WorkerStats(BaseModel):
    user_id: UUID
    name: str
    total_assigned: int
    total_completed: int
    total_pending: int
    completion_rate: float
    pending_old: int
    completed_this_week: int
    completed_this_month: int


class StatsResponse(BaseModel):
    workers: list[WorkerStats]
    global_total_movements: int
    global_total_tasks_completed: int
    global_completion_rate: float
    busiest_day: Optional[str] = None
    most_active_worker: Optional[str] = None

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
    quantity: Optional[int]
    origin_location_id: Optional[UUID]
    destination_location_id: Optional[UUID]
    timestamp: datetime

    model_config = {"from_attributes": True}
