"""暫時性的使用者驗證依賴。"""
from __future__ import annotations

from uuid import UUID

# TODO: 待整合 Supabase Auth 後改由 JWT 解析當前使用者。
DEFAULT_FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def get_current_user_id() -> UUID:
    """回傳目前登入的使用者 ID（暫時使用固定值）。"""

    return DEFAULT_FAKE_USER_ID
