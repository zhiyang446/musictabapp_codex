"""轉譜作業的服務層。"""
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from app.models.tables import JobStatus, SourceType, TranscriptionJob
from app.repositories.jobs import JobRepository
from app.schemas.job import JobCreateRequest


class JobService:
    """封裝作業清單的商業邏輯。"""

    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def create_job(self, *, payload: JobCreateRequest, user_id: UUID) -> TranscriptionJob:
        """建立新的轉譜作業。"""

        job = TranscriptionJob(
            user_id=user_id,
            source_type=SourceType(payload.source_type),
            source_uri=payload.youtube_url,
            storage_object_path=payload.storage_object_path,
            instrument_modes=payload.instrument_modes,
            model_profile=payload.model_profile or 'balanced',
        )
        job.status = JobStatus.PENDING
        job.progress = 0.0
        return self._repository.create_job(job)

    def list_jobs(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[TranscriptionJob], int]:
        """查詢作業列表與總數。"""

        jobs = self._repository.list_jobs(status=status, limit=limit, offset=offset)
        total = self._repository.count_jobs(status=status)
        return jobs, total
