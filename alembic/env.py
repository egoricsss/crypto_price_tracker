import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Импортируем настройки и Base модель
from app.core.config import settings
from app.db.base import Base
from app.models.price import Price  # Импортируем, чтобы Alembic видел модели

# Настройка логгирования Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Устанавливаем target_metadata для autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в 'offline' режиме."""
    url = settings.db.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Настройка контекста для запуска миграций."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Асинхронный запуск миграций.
    
    Создаем движок напрямую из settings, избегая чтения URL из alembic.ini.
    """
    # Создаем async engine напрямую, используя URL из config.py
    connectable = create_async_engine(
        settings.db.database_url,
        poolclass=pool.NullPool,
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск миграций в 'online' режиме."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()