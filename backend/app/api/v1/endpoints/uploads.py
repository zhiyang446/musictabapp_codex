"""上傳相關 API。"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_current_user_id
from app.schemas.upload import UploadAudioRequest, UploadAudioResponse
from app.services.storage_service import (
    StorageService,
    UploadValidationError,
    get_storage_service,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post(
    "/audio",
    response_model=UploadAudioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="產生音訊上傳簽名",
)
async def create_audio_upload(
    payload: UploadAudioRequest,
    storage_service: StorageService = Depends(get_storage_service),
    user_id: UUID = Depends(require_current_user_id),
) -> UploadAudioResponse:
    """建立簽名 URL 供前端直接上傳音訊。"""

    try:
        target = storage_service.create_audio_upload(
            user_id=user_id,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            file_size=payload.file_size,
        )
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": {"code": exc.error_code, "message": exc.message}},
        ) from exc

    return UploadAudioResponse(
        upload_url=target.upload_url,
        method=target.method,
        headers=target.headers,
        expires_at=target.expires_at,
        storage_object_path=target.storage_object_path,
    )
