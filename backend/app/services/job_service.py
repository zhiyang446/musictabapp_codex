"""???????"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.tables import JobEvent, JobStatus, ScoreAsset, TranscriptionJob
from app.repositories.jobs import JobRepository
from app.schemas.job import JobCreateRequest


class JobSubmissionLockedError(Exception):
    """??????????????????"""

    def __init__(self, *, limit: int, active: int) -> None:
        super().__init__("Active job limit reached")
        self.limit = limit
        self.active = active


class JobService:
    """????????????"""

    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def create_job(self, *, payload: JobCreateRequest, user_id: UUID) -> TranscriptionJob:
        """??????????????"""

        active_limit = settings.job_submission_active_limit
        active_count = self._repository.count_jobs_by_statuses(
            user_id=user_id,
            statuses=[JobStatus.PENDING.value, JobStatus.PROCESSING.value],
        )
        if active_count >= active_limit:
            raise JobSubmissionLockedError(limit=active_limit, active=active_count)

        source_uri: Optional[str]
        if payload.source_type == "youtube":
            source_uri = payload.youtube_url
        else:
            source_uri = payload.storage_object_path

        job = TranscriptionJob(
            user_id=user_id,
            source_type=payload.source_type,
            source_uri=source_uri,
            storage_object_path=payload.storage_object_path,
            instrument_modes=payload.instrument_modes,
            model_profile=payload.model_profile or "balanced",
            status=JobStatus.PENDING,
            progress=0.0,
        )
        created_job = self._repository.create_job(job)

        self._repository.create_event(
            job_id=created_job.id,
            stage="submitted",
            message="Job submitted",
            payload={"sourceType": created_job.source_type},
        )

        task_payload: Dict[str, Any] = {
            "source_type": created_job.source_type,
            "source_uri": created_job.source_uri,
            "storage_path": created_job.storage_object_path,
            "instrument_modes": list(created_job.instrument_modes or []),
            "model_profile": created_job.model_profile,
        }
        celery_app.send_task(
            "app.tasks.orchestrator.process_transcription_job",
            args=(str(created_job.id), task_payload),
        )

        return created_job

    def list_jobs(
        self,
        *,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[TranscriptionJob], int]:
        """??????????,?????????"""

        jobs = self._repository.list_jobs(user_id=user_id, status=status, limit=limit, offset=offset)
        total = self._repository.count_jobs(user_id=user_id, status=status)
        return jobs, total

    def get_job(self, *, user_id: UUID, job_id: UUID) -> TranscriptionJob | None:
        """?????????????"""

        return self._repository.get_job(job_id=job_id, user_id=user_id)

    def list_job_assets(self, *, user_id: UUID, job_id: UUID) -> Optional[List[ScoreAsset]]:
        """?????????????????????"""

        job = self._repository.get_job(job_id=job_id, user_id=user_id)
        if job is None:
            return None
        assets = self._repository.list_assets(job_id=job_id, user_id=user_id)
        return sorted(assets, key=lambda item: item.created_at)

    def list_job_events(self, *, user_id: UUID, job_id: UUID) -> Optional[List[JobEvent]]:
        """????????????????"""

        job = self._repository.get_job(job_id=job_id, user_id=user_id)
        if job is None:
            return None
        events = self._repository.list_events(job_id=job_id, user_id=user_id)
        return sorted(events, key=lambda item: item.created_at)

    def get_job_event(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        event_id: UUID,
    ) -> JobEvent | None:
        """??? ID ??????,?????????"""

        return self._repository.get_event(job_id=job_id, user_id=user_id, event_id=event_id)

    def list_job_events_after(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        created_after: datetime | None,
        last_event_id: UUID | None,
    ) -> List[JobEvent]:
        """???????????????"""

        return self._repository.list_events_after(
            job_id=job_id,
            user_id=user_id,
            created_after=created_after,
            last_event_id=last_event_id,
        )


