"""Supabase 儲存相關服務。"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from supabase import Client
from app.core.config import settings
from app.core.supabase import get_supabase_client


@dataclass
class UploadTarget:
    """描述簽名上傳所需的資訊。"""

    upload_url: str
    method: str
    headers: Dict[str, str]
    expires_at: datetime
    storage_object_path: str


class UploadValidationError(Exception):
    """上傳參數驗證錯誤。"""

    def __init__(self, *, status_code: int, error_code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


class StorageService:
    """封裝與 Supabase Storage 的互動。"""

    def __init__(
        self,
        *,
        client: Client,
        bucket: str,
        base_url: str,
        upload_expires: int,
        max_bytes: int,
    ) -> None:
        self._client = client
        self._bucket = bucket
        self._base_url = base_url.rstrip('/')
        self._upload_expires = upload_expires
        self._max_bytes = max_bytes

    def create_audio_upload(
        self,
        *,
        user_id: UUID,
        file_name: str,
        mime_type: str,
        file_size: int,
    ) -> UploadTarget:
        """建立音訊檔案的簽名上傳資訊。"""

        safe_name = self._sanitize_file_name(file_name)
        self._validate_mime_type(mime_type)
        self._validate_file_size(file_size)

        object_name = f"{uuid4().hex}_{safe_name}"
        object_path = f"{user_id}/audio/{object_name}"

        storage = self._client.storage.from_(self._bucket)
        try:
            response = storage.create_signed_upload_url(object_path, self._upload_expires)
        except Exception as exc:  # noqa: B902 - 轉換外部例外為 HTTP 錯誤
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error": {"code": "STORAGE_SERVICE_ERROR", "message": "無法建立簽名上傳網址"}},
            ) from exc

        signed_url = response.get("signedUrl") or response.get("signed_url")
        if not signed_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error": {"code": "STORAGE_SERVICE_ERROR", "message": "Supabase 回傳資料不完整"}},
            )

        upload_url = self._compose_upload_url(signed_url)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._upload_expires)
        headers = {"Content-Type": mime_type}

        return UploadTarget(
            upload_url=upload_url,
            method="PUT",
            headers=headers,
            expires_at=expires_at,
            storage_object_path=object_path,
        )

    def _sanitize_file_name(self, file_name: str) -> str:
        """移除危險字元並保留檔名。"""

        name = file_name.strip()
        name = os.path.basename(name)
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"[^A-Za-z0-9._-]", "-", name)
        name = name[:128]
        if not name or name.startswith('.') or '..' in name:
            raise UploadValidationError(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_FILE_NAME",
                message="檔名格式不合法",
            )
        return name

    def _validate_mime_type(self, mime_type: str) -> None:
        """檢查 MIME 類型是否為音訊。"""

        if not mime_type.lower().startswith("audio/"):
            raise UploadValidationError(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="UNSUPPORTED_MEDIA_TYPE",
                message="僅支援音訊格式上傳",
            )

    def _validate_file_size(self, file_size: int) -> None:
        """確認檔案大小未超過限制。"""

        if file_size <= 0:
            raise UploadValidationError(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_FILE_SIZE",
                message="檔案大小需大於 0",
            )
        if file_size > self._max_bytes:
            raise UploadValidationError(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                error_code="UPLOAD_LIMIT_EXCEEDED",
                message="檔案大小超過限制",
            )

    def _compose_upload_url(self, signed_url: str) -> str:
        """組合最終可使用的上傳 URL。"""

        if signed_url.startswith("http"):
            return signed_url
        return f"{self._base_url}/storage/v1/{signed_url.lstrip('/')}"



_storage_service: StorageService | None = None

def get_storage_service() -> StorageService:
    """提供 FastAPI 依賴注入的 StorageService。"""

    global _storage_service
    if _storage_service is None:
        client = get_supabase_client()
        if not settings.supabase_storage_bucket or not settings.supabase_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": {"code": "STORAGE_CONFIGURATION_ERROR", "message": "尚未設定 Supabase Storage 參數"}},
            )
        _storage_service = StorageService(
            client=client,
            bucket=settings.supabase_storage_bucket,
            base_url=settings.supabase_url,
            upload_expires=settings.upload_signed_url_expires,
            max_bytes=settings.upload_max_bytes,
        )
    return _storage_service
