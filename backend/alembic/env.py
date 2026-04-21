from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from alembic import context
from app.core.config import settings
from app.db.database import Base
from app.models import models

config = context.config

# Comentamos fileConfig para evitar el problema de codificación en Windows
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

target_metadata = Base.metadata

sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+pg8000://")

def run_migrations_online():
    connectable = create_engine(sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()