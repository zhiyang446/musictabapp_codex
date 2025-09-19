"""Alembic 遷移設定。"""
from logging.config import fileConfig
from typing import Any, Dict

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app.core.config import settings

# Alembic 配置物件提供存取 ini 設定
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata 用於追蹤 SQLModel 定義
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """以離線模式執行資料庫遷移。"""

    database_url = settings.supabase_url
    if not database_url:
        raise RuntimeError("SUPABASE_URL 未設定，無法進行離線遷移。")

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """以線上模式執行資料庫遷移。"""

    configuration: Dict[str, Any] = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.supabase_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
