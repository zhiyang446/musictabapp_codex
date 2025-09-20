"""測試 /v1/uploads API 與儲存服務。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.uploads import get_storage_service
from app.core.security import require_current_user_id
from app.main import app
from app.services.storage_service import (
    StorageService,
    UploadTarget,
    UploadValidationError,
)

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000abc")


class FakeStorageService:
    """提供可控回傳結果的假服務。"""

    def __init__(self, target: UploadTarget | None = None, error: UploadValidationError | None = None) -> None:
        self._target = target
        self._error = error

    def create_audio_upload(
        self,
        *,
        user_id: UUID,
        file_name: str,
        mime_type: str,
        file_size: int,
    ) -> UploadTarget:
        if self._error is not None:
            raise self._error
        assert self._target is not None
        return self._target


def override_current_user() -> UUID:
    """回傳測試使用者 ID。"""

    return TEST_USER_ID


def test_create_audio_upload_success() -> None:
    """確認 API 能回傳簽名上傳資訊。"""

    target = UploadTarget(
        upload_url="https://example.supabase.co/storage/v1/signed-upload/demo",
        method="PUT",
        headers={"Content-Type": "audio/wav"},
        expires_at=datetime.now(timezone.utc),
        storage_object_path=f"{TEST_USER_ID}/audio/sample.wav",
    )
    app.dependency_overrides[get_storage_service] = lambda: FakeStorageService(target=target)
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.post(
            "/v1/uploads/audio",
            json={
                "fileName": "demo.wav",
                "mimeType": "audio/wav",
                "fileSize": 1024,
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["uploadUrl"] == target.upload_url
        assert payload["storageObjectPath"] == target.storage_object_path
    finally:
        app.dependency_overrides.pop(get_storage_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_create_audio_upload_validation_error() -> None:
    """當服務回傳驗證錯誤時應得到 400。"""

    error = UploadValidationError(
        status_code=400,
        error_code="INVALID_FILE_NAME",
        message="檔名格式不合法",
    )
    app.dependency_overrides[get_storage_service] = lambda: FakeStorageService(error=error)
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.post(
            "/v1/uploads/audio",
            json={
                "fileName": "../../hack.wav",
                "mimeType": "audio/wav",
                "fileSize": 1024,
            },
        )
        assert response.status_code == 400
        body = response.json()
        assert body["detail"]["error"]["code"] == "INVALID_FILE_NAME"
    finally:
        app.dependency_overrides.pop(get_storage_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_create_audio_upload_size_limit() -> None:
    """超過限制時應得到 413。"""

    error = UploadValidationError(
        status_code=413,
        error_code="UPLOAD_LIMIT_EXCEEDED",
        message="檔案大小超過限制",
    )
    app.dependency_overrides[get_storage_service] = lambda: FakeStorageService(error=error)
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.post(
            "/v1/uploads/audio",
            json={
                "fileName": "demo.wav",
                "mimeType": "audio/wav",
                "fileSize": 999999999,
            },
        )
        assert response.status_code == 413
        body = response.json()
        assert body["detail"]["error"]["code"] == "UPLOAD_LIMIT_EXCEEDED"
    finally:
        app.dependency_overrides.pop(get_storage_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


class StubBucket:
    """模擬 Supabase Storage bucket。"""

    def __init__(self) -> None:
        self.last_path: str | None = None
        self.last_expires: int | None = None

    def create_signed_upload_url(self, path: str, expires_in: int) -> Dict[str, str]:
        self.last_path = path
        self.last_expires = expires_in
        return {"signedUrl": "signed-upload/path?token=abc"}


class StubStorage:
    """模擬 storage.from_ 呼叫。"""

    def __init__(self) -> None:
        self.bucket: str | None = None
        self.bucket_obj = StubBucket()

    def from_(self, bucket: str) -> StubBucket:
        self.bucket = bucket
        return self.bucket_obj


class StubSupabaseClient:
    """簡單的 Supabase client 替身。"""

    def __init__(self) -> None:
        self.storage = StubStorage()


def test_storage_service_generates_expected_path() -> None:
    """驗證 StorageService 會用正確路徑與簽名。"""

    client = StubSupabaseClient()
    service = StorageService(
        client=client,
        bucket="audio-bucket",
        base_url="https://demo.supabase.co",
        upload_expires=600,
        max_bytes=1024 * 1024,
    )
    user_id = uuid4()
    target = service.create_audio_upload(
        user_id=user_id,
        file_name="My Song.wav",
        mime_type="audio/wav",
        file_size=2048,
    )

    assert client.storage.bucket == "audio-bucket"
    assert client.storage.bucket_obj.last_path is not None
    assert client.storage.bucket_obj.last_expires == 600
    assert target.storage_object_path.startswith(f"{user_id}/audio/")
    assert target.upload_url.startswith("https://demo.supabase.co/storage/v1/")
