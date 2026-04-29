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

# --- User ---

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}

# --- Warehouse ---

class WarehouseCreate(BaseModel):
    name: str
    num_shelves: int
    num_levels: int
    num_locations: int

class WarehouseResponse(BaseModel):
    id: UUID
    name: str
    num_shelves: int
    num_levels: int
    num_locations: int
    created_at: datetime

    model_config = {"from_attributes": True}

# --- Warehouse Full (para el Gemelo Digital) ---

class InventoryItemFullResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID]
    box_id: Optional[UUID]
    quantity: Optional[int]

    model_config = {"from_attributes": True}

class LocationFullResponse(BaseModel):
    id: UUID
    position_number: int
    nfc_tag: Optional[str]
    inventory: Optional[InventoryItemFullResponse]

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
    num_levels: int
    num_locations: int
    created_at: datetime
    shelves: list[ShelfFullResponse]

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

# --- Product ---

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    barcode: Optional[str] = None

class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    type: Optional[str]
    barcode: Optional[str]

    model_config = {"from_attributes": True}

# --- Box ---

class BoxCreate(BaseModel):
    product_id: UUID
    current_quantity: int
    max_capacity: int

class BoxResponse(BaseModel):
    id: UUID
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

class TaskStatusUpdate(BaseModel):
    status: TaskStatus

class TaskResponse(BaseModel):
    id: UUID
    created_by: UUID
    assigned_to: UUID
    type: TaskType
    status: TaskStatus
    created_at: datetime

    model_config = {"from_attributes": True}

# --- Movement ---

class MovementCreate(BaseModel):
    task_id: UUID
    type: MovementType
    product_id: Optional[UUID] = None
    box_id: Optional[UUID] = None
    origin_location_id: Optional[UUID] = None
    destination_location_id: Optional[UUID] = None

class MovementResponse(BaseModel):
    id: UUID
    task_id: UUID
    performed_by: UUID
    type: MovementType
    product_id: Optional[UUID]
    box_id: Optional[UUID]
    origin_location_id: Optional[UUID]
    destination_location_id: Optional[UUID]
    timestamp: datetime

    model_config = {"from_attributes": True}