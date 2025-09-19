"""系統健康檢查端點。"""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from app.core.config import settings

# router 專責提供系統層資訊路由
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", summary="查詢系統健康狀態")
async def read_health() -> dict[str, Any]:
    """回傳服務健康狀態與版本資訊，供監控使用。"""

    # payload 字典整理回應內容
    payload: dict[str, Any] = {
        "status": "ok",
        "service": settings.project_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return payload
