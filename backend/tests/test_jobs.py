"""?? /v1/jobs ?? API?"""
from __future__ import annotations

import json

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest

from app.api.v1.endpoints.jobs import get_job_service
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.security import require_current_user_id
from app.main import app
from app.models.tables import JobEvent, JobStatus, ScoreAsset, ScoreFormat, TranscriptionJob
from app.schemas.job import JobCreateRequest
from app.services.job_service import JobService, JobSubmissionLockedError

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000123")


def _utc_now() -> datetime:
    """????? UTC ???"""

    return datetime.now(timezone.utc)


class FakeJobService:
    """?? JobService,???????????????"""

    def __init__(
        self,
        jobs: List[TranscriptionJob],
        assets: Dict[UUID, List[ScoreAsset]] | None = None,
        events: Dict[UUID, List[JobEvent]] | None = None,
    ) -> None:
        self._jobs: Dict[UUID, TranscriptionJob] = {job.id: job for job in jobs}
        self._assets: Dict[UUID, List[ScoreAsset]] = assets or {}
        self._events: Dict[UUID, List[JobEvent]] = events or {}

    def list_job_events(self, *, user_id: UUID, job_id: UUID) -> List[JobEvent] | None:
        """????????????"""

        job = self._jobs.get(job_id)
        if job is None or job.user_id != user_id:
            return None
        events = self._events.get(job_id, [])
        return sorted(events, key=lambda item: item.created_at)

    def get_job_event(self, *, user_id: UUID, job_id: UUID, event_id: UUID) -> JobEvent | None:
        """? ID ?????????"""

        job = self._jobs.get(job_id)
        if job is None or job.user_id != user_id:
            return None
        for event in self._events.get(job_id, []):
            if event.id == event_id:
                return event
        return None

    def list_job_events_after(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        created_after: datetime | None,
        last_event_id: UUID | None,
    ) -> List[JobEvent]:
        """???????????????"""

        job = self._jobs.get(job_id)
        if job is None or job.user_id != user_id:
            return []
        events = sorted(self._events.get(job_id, []), key=lambda item: (item.created_at, item.id))
        if created_after is None:
            return events
        filtered: List[JobEvent] = []
        for event in events:
            if event.created_at > created_after:
                filtered.append(event)
            elif last_event_id is not None and event.created_at == created_after and event.id > last_event_id:
                filtered.append(event)
        return filtered

    def create_job(self, *, payload: JobCreateRequest, user_id: UUID) -> TranscriptionJob:
        """????????????"""

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
        """?????????????"""

        filtered = [job for job in self._jobs.values() if job.user_id == user_id]
        if status:
            filtered = [job for job in filtered if job.status == status]
        sliced = filtered[offset : offset + limit]
        return sliced, len(filtered)

    def get_job(self, *, user_id: UUID, job_id: UUID) -> TranscriptionJob | None:
        """??????,?????????"""

        job = self._jobs.get(job_id)
        if job is None or job.user_id != user_id:
            return None
        return job

    def list_job_assets(self, *, user_id: UUID, job_id: UUID) -> List[ScoreAsset] | None:
        """????????,????????? None?"""

        job = self.get_job(user_id=user_id, job_id=job_id)
        if job is None:
            return None
        assets = self._assets.get(job_id, [])
        return sorted(assets, key=lambda item: item.created_at)


class InMemoryJobRepository:
    """??????????,??????????"""

    def __init__(self) -> None:
        self.jobs: Dict[UUID, TranscriptionJob] = {}
        self.events: Dict[UUID, List[JobEvent]] = {}

    def count_jobs_by_statuses(self, *, user_id: UUID, statuses: List[str]) -> int:
        return sum(1 for job in self.jobs.values() if job.user_id == user_id and job.status in statuses)

    def create_job(self, job: TranscriptionJob) -> TranscriptionJob:
        if job.id is None:
            job.id = uuid4()
        job.created_at = _utc_now()
        job.updated_at = _utc_now()
        self.jobs[job.id] = job
        return job

    def create_event(
        self,
        *,
        job_id: UUID,
        stage: str,
        message: str | None = None,
        payload: Dict[str, Any] | None = None,
    ) -> JobEvent:
        event = JobEvent(
            job_id=job_id,
            stage=stage,
            message=message,
            payload=payload or {},
        )
        event.id = uuid4()
        event.created_at = _utc_now()
        self.events.setdefault(job_id, []).append(event)
        return event

    def get_job(self, *, job_id: UUID, user_id: UUID) -> TranscriptionJob | None:
        job = self.jobs.get(job_id)
        if job is None or job.user_id != user_id:
            return None
        return job

    def list_assets(self, *, job_id: UUID, user_id: UUID) -> List[ScoreAsset]:
        return []

    def list_events(self, *, job_id: UUID, user_id: UUID) -> List[JobEvent]:
        job = self.get_job(job_id=job_id, user_id=user_id)
        if job is None:
            return []
        return sorted(self.events.get(job_id, []), key=lambda item: item.created_at)


def build_job_model(status: str) -> TranscriptionJob:
    """?????????????"""

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
    """???????????"""

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


def build_event_model(
    *,
    job_id: UUID,
    stage: str,
    message: str,
    payload: Dict[str, Any] | None,
    created_at: datetime,
) -> JobEvent:
    """?????????????"""

    event = JobEvent(
        job_id=job_id,
        stage=stage,
        message=message,
        payload=payload or {},
    )
    event.id = uuid4()
    event.created_at = created_at
    return event


def override_job_service() -> JobService:
    """????? FakeJobService?"""

    jobs = [
        build_job_model("completed"),
        build_job_model("processing"),
    ]
    return FakeJobService(jobs)  # type: ignore[return-value]


def override_current_user() -> UUID:
    """????????? ID?"""

    return TEST_USER_ID


def test_list_jobs_returns_data() -> None:
    """???? API ????????????"""

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
    """???? API ???????"""

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
    """?????????? pending ???"""

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
    """????????????????"""

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
    """?????????????? 404?"""

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
    """??????????????????????"""

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
        # ?? createdAt ????
        assert payload["data"][0]["format"] == ScoreFormat.MUSICXML.value
        assert payload["data"][1]["format"] == ScoreFormat.PDF.value
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_list_job_assets_empty() -> None:
    """?????????????????"""

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
    """?????????????????? 404?"""

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

def test_list_job_events_success() -> None:
    """????????????"""

    job = build_job_model("processing")
    events = {
        job.id: [
            build_event_model(
                job_id=job.id,
                stage="render_start",
                message="??????",
                payload={"step": "render"},
                created_at=_utc_now() + timedelta(minutes=5),
            ),
            build_event_model(
                job_id=job.id,
                stage="audio_ingest",
                message="??????",
                payload={"source": "youtube"},
                created_at=_utc_now(),
            ),
        ]
    }
    service = FakeJobService([job], events=events)
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get(f"/v1/jobs/{job.id}/events")
        assert response.status_code == 200
        body = response.json()
        assert [item["stage"] for item in body["data"]] == ["audio_ingest", "render_start"]
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_list_job_events_empty() -> None:
    """??????????"""

    job = build_job_model("processing")
    service = FakeJobService([job], events={job.id: []})
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get(f"/v1/jobs/{job.id}/events")
        assert response.status_code == 200
        assert response.json()["data"] == []
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_list_job_events_not_found() -> None:
    """??????????????? 404?"""

    other_job = build_job_model("completed")
    other_job.user_id = UUID("00000000-0000-0000-0000-000000000999")
    service = FakeJobService([other_job])
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response_missing = client.get(f"/v1/jobs/{uuid4()}/events")
        assert response_missing.status_code == 404

        response_other = client.get(f"/v1/jobs/{other_job.id}/events")
        assert response_other.status_code == 404
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_service_create_job_enqueues_task(monkeypatch: pytest.MonkeyPatch) -> None:
    """????????????? Celery ???"""

    repository = InMemoryJobRepository()
    service = JobService(repository)
    monkeypatch.setattr(settings, "job_submission_active_limit", 3, raising=False)
    sent_tasks: list[tuple[Any, Any, Any]] = []
    monkeypatch.setattr(
        celery_app,
        "send_task",
        lambda name, args=(), kwargs=None: sent_tasks.append((name, args, kwargs)),
    )

    payload = JobCreateRequest(
        source_type="local",
        storage_object_path="user/audio/demo.wav",
        youtube_url=None,
        instrument_modes=["guitar"],
        model_profile="balanced",
        tempo_hint=None,
        time_signature=None,
    )

    job = service.create_job(payload=payload, user_id=TEST_USER_ID)

    assert job.status == JobStatus.PENDING
    events = repository.list_events(job_id=job.id, user_id=TEST_USER_ID)
    assert len(events) == 1
    assert events[0].stage == "submitted"
    assert sent_tasks and sent_tasks[0][0] == "app.tasks.orchestrator.process_transcription_job"


def test_service_create_job_respects_active_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """???????? JobSubmissionLockedError?"""

    repository = InMemoryJobRepository()
    service = JobService(repository)
    monkeypatch.setattr(settings, "job_submission_active_limit", 1, raising=False)
    monkeypatch.setattr(celery_app, "send_task", lambda *args, **kwargs: None)

    existing = build_job_model("processing")
    existing.status = JobStatus.PROCESSING.value
    repository.jobs[existing.id] = existing

    payload = JobCreateRequest(
        source_type="youtube",
        storage_object_path=None,
        youtube_url="https://youtu.be/another",
        instrument_modes=["piano"],
        model_profile="balanced",
        tempo_hint=None,
        time_signature=None,
    )

    with pytest.raises(JobSubmissionLockedError) as exc:
        service.create_job(payload=payload, user_id=TEST_USER_ID)
    assert exc.value.limit == 1


def test_stream_job_events_initial_payload() -> None:
    """?????????????????"""

    job = build_job_model("processing")
    earlier = build_event_model(
        job_id=job.id,
        stage="audio_ingest",
        message="????",
        created_at=_utc_now(),
        payload={},
    )
    later = build_event_model(
        job_id=job.id,
        stage="render_start",
        message="????",
        created_at=_utc_now() + timedelta(seconds=5),
        payload={},
    )
    service = FakeJobService([job], events={job.id: [later, earlier]})
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        payload = ""
        with client.stream("GET", f"/v1/jobs/{job.id}/stream") as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            for chunk in response.iter_content(chunk_size=None):
                payload += chunk.decode("utf-8")
                if "event:render_start" in payload:
                    break

        blocks = [block for block in payload.strip().split("\n\n") if block]

        stages = [line.removeprefix("event:") for block in blocks for line in block.splitlines() if line.startswith("event:")]
        assert stages == ["audio_ingest", "render_start"]

        data_entries = [json.loads(line.removeprefix("data:")) for block in blocks for line in block.splitlines() if line.startswith("data:")]
        assert data_entries and data_entries[0]["stage"] == "audio_ingest"
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_stream_job_events_with_last_event_header() -> None:
    """Last-Event-ID ??????????"""

    job = build_job_model("processing")
    first = build_event_model(
        job_id=job.id,
        stage="audio_ingest",
        message="????",
        created_at=_utc_now(),
        payload={},
    )
    second = build_event_model(
        job_id=job.id,
        stage="render_start",
        message="????",
        created_at=_utc_now() + timedelta(seconds=1),
        payload={},
    )
    service = FakeJobService([job], events={job.id: [first, second]})
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        payload = ""
        with client.stream(
            "GET",
            f"/v1/jobs/{job.id}/stream",
            headers={"Last-Event-ID": str(first.id)},
        ) as response:
            assert response.status_code == 200
            for chunk in response.iter_content(chunk_size=None):
                payload += chunk.decode("utf-8")
                break

        assert "event:render_start" in payload
        assert "audio_ingest" not in payload
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_stream_job_events_invalid_header() -> None:
    """Last-Event-ID ??????? 400?"""

    job = build_job_model("processing")
    service = FakeJobService([job])
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get(f"/v1/jobs/{job.id}/stream", headers={"Last-Event-ID": "not-a-uuid"})
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "INVALID_LAST_EVENT_ID"
        assert body["error"]["message"] == "Last-Event-ID 必須為 UUID"
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)


def test_stream_job_events_job_not_found() -> None:
    """???????????? 404?"""

    job = build_job_model("completed")
    job.user_id = UUID("00000000-0000-0000-0000-000000000999")
    service = FakeJobService([job])
    app.dependency_overrides[get_job_service] = lambda: service  # type: ignore[return-value]
    app.dependency_overrides[require_current_user_id] = override_current_user
    client = TestClient(app)

    try:
        response = client.get(f"/v1/jobs/{job.id}/stream")
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "JOB_NOT_FOUND"
        assert body["error"]["message"] == "Job not found"
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(require_current_user_id, None)



