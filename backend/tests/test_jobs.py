"""/v1/jobs API 測試。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.v1.endpoints.jobs import get_job_service
from app.core.security import get_current_user_id
from app.main import app
from app.models.tables import TranscriptionJob
from app.schemas.job import JobCreateRequest
from app.services.job_service import JobService

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000123")


class FakeJobService:
    """測試用的 JobService，回傳固定資料。"""

    def __init__(self, jobs: List[TranscriptionJob]) -> None:
        self._jobs = jobs

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
        return job

    def list_jobs(
        self,
        *,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[TranscriptionJob], int]:
        filtered = self._jobs
        if status:
            filtered = [job for job in filtered if job.status == status]
        return filtered[offset : offset + limit], len(filtered)


def build_job_model(status: str) -> TranscriptionJob:
    """建立測試用的作業模型。"""

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
    app.dependency_overrides[get_job_service] = override_job_service
    app.dependency_overrides[get_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get('/v1/jobs')
        assert response.status_code == 200
        payload = response.json()
        assert payload['total'] == 2
        assert len(payload['data']) == 2
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(get_current_user_id, None)


def test_list_jobs_filter_by_status() -> None:
    app.dependency_overrides[get_job_service] = override_job_service
    app.dependency_overrides[get_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get('/v1/jobs', params={'status': 'completed'})
        assert response.status_code == 200
        payload = response.json()
        assert payload['total'] == 1
        assert payload['data'][0]['status'] == 'completed'
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(get_current_user_id, None)


def test_create_job_success() -> None:
    app.dependency_overrides[get_job_service] = override_job_service
    app.dependency_overrides[get_current_user_id] = override_current_user
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
        app.dependency_overrides.pop(get_current_user_id, None)
