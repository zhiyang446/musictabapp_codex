"""Pydantic schemas for job resources."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobCreateRequest(BaseModel):
    """建立作業的請求負載。"""

    model_config = ConfigDict(populate_by_name=True)

    source_type: str = Field(validation_alias="sourceType")
    storage_object_path: str | None = Field(default=None, validation_alias="storageObjectPath")
    youtube_url: str | None = Field(default=None, validation_alias="youtubeUrl")
    instrument_modes: List[str] = Field(validation_alias="instrumentModes")
    model_profile: str | None = Field(default=None, validation_alias="modelProfile")
    tempo_hint: int | None = Field(default=None, validation_alias="tempoHint")
    time_signature: str | None = Field(default=None, validation_alias="timeSignature")

    @model_validator(mode="after")
    def validate_payload(self) -> "JobCreateRequest":
        if self.source_type not in {"local", "youtube"}:
            raise ValueError("sourceType must be 'local' or 'youtube'")
        if self.source_type == "local" and not self.storage_object_path:
            raise ValueError("storageObjectPath is required for local source")
        if self.source_type == "youtube" and not self.youtube_url:
            raise ValueError("youtubeUrl is required for youtube source")
        if not self.instrument_modes:
            raise ValueError("instrumentModes cannot be empty")
        return self


class JobResource(BaseModel):
    """API 回傳的作業資源。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: str = Field(serialization_alias="sourceType")
    source_uri: Optional[str] = Field(default=None, serialization_alias="sourceUri")
    storage_object_path: Optional[str] = Field(default=None, serialization_alias="storageObjectPath")
    instrument_modes: List[str] = Field(serialization_alias="instrumentModes")
    model_profile: str = Field(serialization_alias="modelProfile")
    status: str
    progress: float
    error_message: Optional[str] = Field(default=None, serialization_alias="errorMessage")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class JobListResponse(BaseModel):
    """作業列表回應包裝。"""

    data: List[JobResource]
    total: int

