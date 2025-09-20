"""測試 /v1/jobs 相關 API。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.jobs import get_job_service
from app.core.security import require_current_user_id
from app.main import app
from app.models.tables import ScoreAsset, ScoreFormat, TranscriptionJob
from app.schemas.job import JobCreateRequest
from app.services.job_service import JobService

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000123")


def _utc_now() -> datetime:
    """回傳目前的 UTC 時間。"""

    return datetime.now(timezone.utc)


class FakeJobService:
    """替身 JobService，提供測試可用的作業與資產資料。"""

    def __init__(
        self,
        jobs: List[TranscriptionJob],
        assets: Dict[UUID, List[ScoreAsset]] | None = None,
    ) -> None:
        self._jobs: Dict[UUID, TranscriptionJob] = {job.id: job for job in jobs}
        self._assets: Dict[UUID, List[ScoreAsset]] = assets or {}

    def create_job(self, *, payload: JobCreateRequest, user_id: UUID) -> TranscriptionJob:
        """建立作業並回傳模型物件。"""

        job = TranscriptionJob(
            user_id=user_id,
            source_type=payload.source_type,
            source_uri=payload.youtube_url,
            storage_object_path=payload.storage_object_path,
            instrument_modes=payload.instrument_modes,
            model_profile=payload.model_profile or "balanced",
        )
        job.status = "pending"
        job.progress = 0.0
        job.id = uuid4()
        job.created_at = _utc_now()
        job.updated_at = _utc_now()
        self._jobs[job.id] = job
        return job

    def list_jobs(
        self,
        *,
        user_id: UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[TranscriptionJob], int]:
        """依條件回傳作業清單與筆數。"""

        filtered = [job for job in self._jobs.values() if job.user_id == user_id]
        if status:
            filtered = [job for job in filtered if job.status == status]
        sliced = filtered[offset : offset + limit]
        return sliced, len(filtered)

    def get_job(self, *, user_id: UUID, job_id: UUID) -> TranscriptionJob | None:
        """取得指定作業，僅允許擁有者存取。"""

        job = self._jobs.get(job_id)
        if job is None or job.user_id != user_id:
            return None
        return job

    def list_job_assets(self, *, user_id: UUID, job_id: UUID) -> List[ScoreAsset] | None:
        """回傳作業資產清單，若作業不存在則回傳 None。"""

        job = self.get_job(user_id=user_id, job_id=job_id)
        if job is None:
            return None
        assets = self._assets.get(job_id, [])
        return sorted(assets, key=lambda item: item.created_at)


def build_job_model(status: str) -> TranscriptionJob:
    """建立具預設欄位的作業模型。"""

    job = TranscriptionJob(
        user_id=TEST_USER_ID,
        source_type="youtube",
        source_uri="https://youtu.be/demo",
        storage_object_path=None,
        instrument_modes=["guitar"],
        model_profile="balanced",
        status=status,
        progress=42.5,
        error_message=None,
    )
    job.id = uuid4()
    job.created_at = _utc_now()
    job.updated_at = _utc_now()
    return job


def build_asset_model(
    *,
    job_id: UUID,
    instrument: str,
    score_format: ScoreFormat,
    created_at: datetime,
    storage_path: str,
) -> ScoreAsset:
    """建立測試用的資產模型。"""

    asset = ScoreAsset(
        job_id=job_id,
        instrument=instrument,
        format=score_format,
        storage_object_path=storage_path,
        duration_seconds=210,
        page_count=4,
    )
    asset.id = uuid4()
    asset.created_at = created_at
    return asset


def override_job_service() -> JobService:
    """建立預設的 FakeJobService。"""

    jobs = [
        build_job_model("completed"),
        build_job_model("processing"),
    ]
    return FakeJobService(jobs)  # type: ignore[return-value]


def override_current_user() -> UUID:
    """回傳測試用的使用者 ID。"""

    return TEST_USER_ID


def test_list_jobs_returns_data() -> None:
    """確認列表 API 可回傳全部作業與總筆數。"""

    app.dependency_overrides[get_job_service] = override_job_service
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get("/v1/jobs")
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 2
        assert len(payload["data"]) == 2
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_list_jobs_filter_by_status() -> None:
    """確認列表 API 可依狀態過濾。"""

    app.dependency_overrides[get_job_service] = override_job_service
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get("/v1/jobs", params={"status": "completed"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["data"][0]["status"] == "completed"
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_create_job_success() -> None:
    """確認建立作業成功回傳 pending 狀態。"""

    app.dependency_overrides[get_job_service] = override_job_service
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        payload = {
            "sourceType": "youtube",
            "youtubeUrl": "https://youtu.be/demo123",
            "instrumentModes": ["guitar", "drums"],
            "modelProfile": "balanced",
            "tempoHint": 120,
            "timeSignature": "4/4",
            "storageObjectPath": None,
        }
        response = client.post("/v1/jobs", json=payload)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"
        assert body["instrumentModes"] == ["guitar", "drums"]
        assert body["sourceUri"] == "https://youtu.be/demo123"
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_retrieve_job_success() -> None:
    """確認可取得屬於使用者的單筆作業。"""

    job = build_job_model("completed")
    service = FakeJobService([job])
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get(f"/v1/jobs/{job.id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == str(job.id)
        assert payload["status"] == job.status
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_retrieve_job_not_found() -> None:
    """當作業不存在或非本人時應回傳 404。"""

    other_job = build_job_model("completed")
    other_job.user_id = UUID("00000000-0000-0000-0000-000000000999")
    service = FakeJobService([other_job])
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        missing_id = uuid4()
        response_missing = client.get(f"/v1/jobs/{missing_id}")
        assert response_missing.status_code == 404

        response_other = client.get(f"/v1/jobs/{other_job.id}")
        assert response_other.status_code == 404
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_list_job_assets_success() -> None:
    """確認可取得指定作業的資產列表並保持時間排序。"""

    job = build_job_model("completed")
    assets = {
        job.id: [
            build_asset_model(
                job_id=job.id,
                instrument="guitar",
                score_format=ScoreFormat.PDF,
                created_at=_utc_now() + timedelta(minutes=5),
                storage_path="user/demo/pdf",
            ),
            build_asset_model(
                job_id=job.id,
                instrument="guitar",
                score_format=ScoreFormat.MUSICXML,
                created_at=_utc_now(),
                storage_path="user/demo/musicxml",
            ),
        ]
    }
    service = FakeJobService([job], assets=assets)
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get(f"/v1/jobs/{job.id}/assets")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["data"]) == 2
        # 應依 createdAt 升序排列
        assert payload["data"][0]["format"] == ScoreFormat.MUSICXML.value
        assert payload["data"][1]["format"] == ScoreFormat.PDF.value
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_list_job_assets_empty() -> None:
    """作業存在但尚無資產時應回傳空陣列。"""

    job = build_job_model("processing")
    service = FakeJobService([job])
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get(f"/v1/jobs/{job.id}/assets")
        assert response.status_code == 200
        payload = response.json()
        assert payload["data"] == []
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_list_job_assets_not_found() -> None:
    """當作業不存在或非本人時列出資產應回傳 404。"""

    other_job = build_job_model("completed")
    other_job.user_id = UUID("00000000-0000-0000-0000-000000000999")
    service = FakeJobService([other_job])
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        missing_id = uuid4()
        response_missing = client.get(f"/v1/jobs/{missing_id}/assets")
        assert response_missing.status_code == 404

        response_other = client.get(f"/v1/jobs/{other_job.id}/assets")
        assert response_other.status_code == 404
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)
