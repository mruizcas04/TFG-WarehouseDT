"""Borra y recrea todas las tablas desde los modelos actuales."""
import asyncio
from sqlalchemy import text
from app.db.database import engine, Base
import app.models.models  # noqa: F401 — registra todos los modelos en Base.metadata

async def reset():
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    print("OK — tablas recreadas")

asyncio.run(reset())
