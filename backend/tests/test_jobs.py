from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Tuple
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.jobs import get_job_service
from app.core.security import require_current_user_id
from app.main import app
from app.models.tables import ScoreAsset, TranscriptionJob
from app.schemas.job import JobCreateRequest
from app.services.job_service import JobService

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000123")


class FakeJobService:
    """替身 JobService，提供測試用資料。"""

    def __init__(self, jobs: List[TranscriptionJob], assets: Dict[UUID, List[ScoreAsset]] | None = None) -> None:
        self._jobs: Dict[UUID, TranscriptionJob] = {job.id: job for job in jobs}
        self._assets: Dict[UUID, List[ScoreAsset]] = assets or {}

    def create_job(self, *, payload: JobCreateRequest, user_id: UUID) -> TranscriptionJob:
        job = TranscriptionJob(
            user_id=user_id,
            source_type=payload.source_type,
            source_uri=payload.youtube_url,
            storage_object_path=payload.storage_object_path,
            instrument_modes=payload.instrument_modes,
            model_profile=payload.model_profile or 'balanced',
        )
        job.status = 'pending'
        job.progress = 0.0
        job.id = uuid4()
        job.created_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
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
        filtered = [job for job in self._jobs.values() if job.user_id == user_id]
        if status:
            filtered = [job for job in filtered if job.status == status]
        sliced = filtered[offset : offset + limit]
        return sliced, len(filtered)

    def get_job(self, *, user_id: UUID, job_id: UUID) -> TranscriptionJob | None:
        job = self._jobs.get(job_id)
        if job is None or job.user_id != user_id:
            return None
        return job

    def list_job_assets(self, *, user_id: UUID, job_id: UUID) -> List[ScoreAsset] | None:
        job = self.get_job(user_id=user_id, job_id=job_id)
        if job is None:
            return None
        return self._assets.get(job_id, [])


def build_job_model(status: str) -> TranscriptionJob:
    """建立具備預設欄位的作業模型。"""

    job = TranscriptionJob(
        user_id=TEST_USER_ID,
        source_type='youtube',
        source_uri='https://youtu.be/demo',
        storage_object_path=None,
        instrument_modes=['guitar'],
        model_profile='balanced',
        status=status,
        progress=42.5,
        error_message=None,
    )
    job.id = uuid4()
    job.created_at = datetime.now(timezone.utc)
    job.updated_at = datetime.now(timezone.utc)
    return job


def override_job_service() -> JobService:
    jobs = [
        build_job_model('completed'),
        build_job_model('processing'),
    ]
    return FakeJobService(jobs)  # type: ignore[return-value]


def override_current_user() -> UUID:
    return TEST_USER_ID


def test_list_jobs_returns_data() -> None:
    """確認列表 API 可回傳全部作業與總筆數。"""

    app.dependency_overrides[get_job_service] = override_job_service
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get('/v1/jobs')
        assert response.status_code == 200
        payload = response.json()
        assert payload['total'] == 2
        assert len(payload['data']) == 2
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_list_jobs_filter_by_status() -> None:
    """確認列表 API 可依狀態過濾。"""

    app.dependency_overrides[get_job_service] = override_job_service
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get('/v1/jobs', params={'status': 'completed'})
        assert response.status_code == 200
        payload = response.json()
        assert payload['total'] == 1
        assert payload['data'][0]['status'] == 'completed'
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
            'sourceType': 'youtube',
            'youtubeUrl': 'https://youtu.be/demo123',
            'instrumentModes': ['guitar', 'drums'],
            'modelProfile': 'balanced',
            'tempoHint': 120,
            'timeSignature': '4/4',
            'storageObjectPath': None,
        }
        response = client.post('/v1/jobs', json=payload)
        assert response.status_code == 201
        body = response.json()
        assert body['status'] == 'pending'
        assert body['instrumentModes'] == ['guitar', 'drums']
        assert body['sourceUri'] == 'https://youtu.be/demo123'
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_retrieve_job_success() -> None:
    """確認可取得屬於使用者的單筆作業。"""

    job = build_job_model('completed')
    service = FakeJobService([job])
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get(f'/v1/jobs/{job.id}')
        assert response.status_code == 200
        payload = response.json()
        assert payload['id'] == str(job.id)
        assert payload['status'] == job.status
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_retrieve_job_not_found() -> None:
    """當作業不存在或非本人時應回傳 404。"""

    other_job = build_job_model('completed')
    other_job.user_id = UUID('00000000-0000-0000-0000-000000000999')
    service = FakeJobService([other_job])
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        missing_id = uuid4()
        response = client.get(f'/v1/jobs/{missing_id}')
        assert response.status_code == 404

        response_other = client.get(f'/v1/jobs/{other_job.id}')
        assert response_other.status_code == 404
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)

