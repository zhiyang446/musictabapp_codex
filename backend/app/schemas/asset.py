"""Score asset API schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScoreAssetResource(BaseModel):
    """API 回傳的譜面資產資訊。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID = Field(serialization_alias="jobId")
    instrument: str
    format: str
    storage_object_path: str = Field(serialization_alias="storageObjectPath")
    duration_seconds: Optional[int] = Field(default=None, serialization_alias="durationSeconds")
    page_count: Optional[int] = Field(default=None, serialization_alias="pageCount")
    created_at: datetime = Field(serialization_alias="createdAt")


class ScoreAssetListResponse(BaseModel):
    """譜面資產列表回應。"""

    data: List[ScoreAssetResource]

