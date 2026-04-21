import asyncio
from app.db.database import AsyncSessionLocal
from app.models.models import User, UserRole
from app.core.security import get_password_hash
import uuid

async def create_admin():
    async with AsyncSessionLocal() as db:
        admin = User(
            id=uuid.uuid4(),
            name="Admin",
            email="admin@warehouse.com",
            password_hash=get_password_hash("admin123"),
            role=UserRole.admin
        )
        db.add(admin)
        await db.commit()
        print("Admin creado correctamente")
        print(f"Email: admin@warehouse.com")
        print(f"Password: admin123")

if __name__ == "__main__":
    asyncio.run(create_admin())