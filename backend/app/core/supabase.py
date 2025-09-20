"""Supabase Client 工具。"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from supabase import Client, create_client

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """建立或取得共用 Supabase Client。"""

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("Supabase URL 或 Service Role Key 未設定")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
