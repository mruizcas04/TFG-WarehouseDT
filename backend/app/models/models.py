import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, Enum, DateTime, Text, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
import enum

# --- Enums ---

class UserRole(enum.Enum):
    admin = "admin"
    worker = "worker"

class TaskType(enum.Enum):
    entrada = "entrada"
    salida = "salida"
    traslado = "traslado"

class TaskStatus(enum.Enum):
    pendiente = "pendiente"
    en_curso = "en_curso"
    completada = "completada"

class MovementType(enum.Enum):
    entrada = "entrada"
    salida = "salida"
    traslado = "traslado"

# --- Modelos ---

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship("User", back_populates="company")
    warehouses: Mapped[list["Warehouse"]] = relationship("Warehouse", back_populates="company")
    products: Mapped[list["Product"]] = relationship("Product", back_populates="company")
    categories: Mapped[list["Category"]] = relationship("Category", back_populates="company")
    boxes: Mapped[list["Box"]] = relationship("Box", back_populates="company")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="company")
    movements: Mapped[list["Movement"]] = relationship("Movement", back_populates="company")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    num_shelves: Mapped[int] = mapped_column(Integer, nullable=False)
    num_levels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_locations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_locations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company | None"] = relationship("Company", back_populates="warehouses")
    shelves: Mapped[list["Shelf"]] = relationship("Shelf", back_populates="warehouse", cascade="all, delete-orphan")


class Shelf(Base):
    __tablename__ = "shelves"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    aisle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    shelf_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_double: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="shelves")
    levels: Mapped[list["Level"]] = relationship("Level", back_populates="shelf", cascade="all, delete-orphan")


class Level(Base):
    __tablename__ = "levels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shelf_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shelves.id"), nullable=False)
    level_number: Mapped[int] = mapped_column(Integer, nullable=False)

    shelf: Mapped["Shelf"] = relationship("Shelf", back_populates="levels")
    locations: Mapped[list["Location"]] = relationship("Location", back_populates="level", cascade="all, delete-orphan")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("levels.id"), nullable=False)
    position_number: Mapped[int] = mapped_column(Integer, nullable=False)
    nfc_tag: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)

    level: Mapped["Level"] = relationship("Level", back_populates="locations")
    inventory_item: Mapped["InventoryItem | None"] = relationship("InventoryItem", back_populates="location", uselist=False)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False, default="#888780")

    company: Mapped["Company | None"] = relationship("Company", back_populates="categories")
    products: Mapped[list["Product"]] = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("company_id", "barcode", name="uq_product_company_barcode"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str | None] = mapped_column(String, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String, nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    units_per_location: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)

    company: Mapped["Company | None"] = relationship("Company", back_populates="products")
    category: Mapped["Category | None"] = relationship("Category", back_populates="products")
    boxes: Mapped[list["Box"]] = relationship("Box", back_populates="product")


class Box(Base):
    __tablename__ = "boxes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    current_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    company: Mapped["Company | None"] = relationship("Company", back_populates="boxes")
    product: Mapped["Product"] = relationship("Product", back_populates="boxes")
    inventory_item: Mapped["InventoryItem | None"] = relationship("InventoryItem", back_populates="box", uselist=False)


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, unique=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    box_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("boxes.id"), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    location: Mapped["Location"] = relationship("Location", back_populates="inventory_item")
    product: Mapped["Product | None"] = relationship("Product")
    box: Mapped["Box | None"] = relationship("Box", back_populates="inventory_item")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="false")
    verification_token: Mapped[str | None] = mapped_column(String, nullable=True)
    reset_password_token: Mapped[str | None] = mapped_column(String, nullable=True)
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company | None"] = relationship("Company", back_populates="users")
    tasks_assigned: Mapped[list["Task"]] = relationship("Task", foreign_keys="Task.assigned_to", back_populates="worker")
    tasks_created: Mapped[list["Task"]] = relationship("Task", foreign_keys="Task.created_by", back_populates="admin")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[TaskType] = mapped_column(Enum(TaskType), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False, default=TaskStatus.pendiente)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    box_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("boxes.id"), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    destination_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company | None"] = relationship("Company", back_populates="tasks")
    admin: Mapped["User"] = relationship("User", foreign_keys=[created_by], back_populates="tasks_created")
    worker: Mapped["User"] = relationship("User", foreign_keys=[assigned_to], back_populates="tasks_assigned")
    product: Mapped["Product | None"] = relationship("Product", foreign_keys=[product_id])
    box: Mapped["Box | None"] = relationship("Box", foreign_keys=[box_id])
    origin_location: Mapped["Location | None"] = relationship("Location", foreign_keys=[origin_location_id])
    destination_location: Mapped["Location | None"] = relationship("Location", foreign_keys=[destination_location_id])
    movements: Mapped[list["Movement"]] = relationship("Movement", back_populates="task")


class Movement(Base):
    __tablename__ = "movements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    performed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    box_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("boxes.id"), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    destination_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company | None"] = relationship("Company", back_populates="movements")
    task: Mapped["Task"] = relationship("Task", back_populates="movements")
    performed_by_user: Mapped["User"] = relationship("User", foreign_keys=[performed_by])
    product: Mapped["Product | None"] = relationship("Product", foreign_keys=[product_id])
    box: Mapped["Box | None"] = relationship("Box", foreign_keys=[box_id])
    origin_location: Mapped["Location | None"] = relationship("Location", foreign_keys=[origin_location_id])
    destination_location: Mapped["Location | None"] = relationship("Location", foreign_keys=[destination_location_id])
