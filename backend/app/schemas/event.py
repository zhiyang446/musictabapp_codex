"""事件相關的 Pydantic Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


class JobEventResource(BaseModel):
    """描述單筆作業事件。"""

    model_config = ConfigDict(from_attributes=True)

    stage: str
    message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(serialization_alias="createdAt")


class JobEventListResponse(BaseModel):
    """包裝事件列表。"""

    data: List[JobEventResource]
