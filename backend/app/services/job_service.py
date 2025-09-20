"""轉譜作業的服務層。"""
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from app.models.tables import ScoreAsset, TranscriptionJob
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
            source_type=payload.source_type,
            source_uri=payload.youtube_url,
            storage_object_path=payload.storage_object_path,
            instrument_modes=payload.instrument_modes,
            model_profile=payload.model_profile or 'balanced',
        )
        return self._repository.create_job(job)

    def list_jobs(
        self,
        *,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[TranscriptionJob], int]:
        """查詢作業列表與總數。"""

        jobs = self._repository.list_jobs(user_id=user_id, status=status, limit=limit, offset=offset)
        total = self._repository.count_jobs(user_id=user_id, status=status)
        return jobs, total

    def get_job(self, *, user_id: UUID, job_id: UUID) -> TranscriptionJob | None:
        """取得單一作業。"""

        return self._repository.get_job(job_id=job_id, user_id=user_id)

    def list_job_assets(self, *, user_id: UUID, job_id: UUID) -> Optional[List[ScoreAsset]]:
        """取得指定作業的資產列表，僅允許作業擁有者存取。"""

        job = self._repository.get_job(job_id=job_id, user_id=user_id)
        if job is None:
            return None
        assets = self._repository.list_assets(job_id=job_id, user_id=user_id)
        return sorted(assets, key=lambda item: item.created_at)
