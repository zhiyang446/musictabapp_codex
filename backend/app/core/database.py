"""資料庫連線與 Session 工具。"""
from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# 建立 SQLModel 專用 engine，使用 Supabase 連線字串。
engine = create_engine(
    settings.supabase_url,
    echo=False,
    pool_pre_ping=True,
)


def get_session() -> Iterator[Session]:
    """提供資料庫 Session 供 FastAPI 相依注入使用。"""

    with Session(engine) as session:
        yield session


__all__ = ["engine", "get_session", "SQLModel", "Session"]
