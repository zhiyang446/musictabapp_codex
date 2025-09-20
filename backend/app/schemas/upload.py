"""上傳相關的 Pydantic Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Dict

from pydantic import BaseModel, ConfigDict, Field


class UploadAudioRequest(BaseModel):
    """音訊上傳請求的輸入資料。"""

    model_config = ConfigDict(populate_by_name=True)

    file_name: str = Field(validation_alias="fileName")
    mime_type: str = Field(validation_alias="mimeType")
    file_size: int = Field(validation_alias="fileSize", ge=1)


class UploadAudioResponse(BaseModel):
    """簽名上傳資訊的回傳格式。"""

    model_config = ConfigDict(populate_by_name=True)

    upload_url: str = Field(serialization_alias="uploadUrl")
    method: str
    headers: Dict[str, str]
    expires_at: datetime = Field(serialization_alias="expiresAt")
    storage_object_path: str = Field(serialization_alias="storageObjectPath")
