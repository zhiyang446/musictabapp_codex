"""任務層日誌工具。"""
from __future__ import annotations

from typing import Any

from loguru import logger


def emit_log(stage: str, message: str, **payload: Any) -> None:
    """輸出任務相關日誌，便於追蹤。"""

    logger.bind(stage=stage).info(message, **payload)
