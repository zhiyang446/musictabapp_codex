"""轉譜作業的資料存取層。"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlmodel import Session

from app.models.tables import ScoreAsset, TranscriptionJob


class JobRepository:
    """封裝轉譜作業相關的資料庫操作。"""

    def __init__(self, session: Session) -> None:
        """建立 Repository 並注入資料庫 Session。"""

        self._session = session

    def create_job(self, job: TranscriptionJob) -> TranscriptionJob:
        """建立新作業並回傳持久化後的資料。"""

        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def get_job(self, *, job_id: UUID, user_id: UUID) -> TranscriptionJob | None:
        """依使用者與作業 ID 取得作業。"""

        statement = select(TranscriptionJob).where(
            TranscriptionJob.id == job_id,
            TranscriptionJob.user_id == user_id,
        )
        return self._session.exec(statement).first()

    def list_jobs(
        self,
        *,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[TranscriptionJob]:
        """依條件取得作業列表。"""

        statement = (
            select(TranscriptionJob)
            .where(TranscriptionJob.user_id == user_id)
            .order_by(TranscriptionJob.created_at.desc())
        )
        if status:
            statement = statement.where(TranscriptionJob.status == status)
        statement = statement.offset(offset).limit(limit)
        return self._session.exec(statement).all()

    def count_jobs(self, *, user_id: UUID, status: Optional[str] = None) -> int:
        """計算作業總量，用於分頁。"""

        statement = select(func.count()).select_from(TranscriptionJob).where(
            TranscriptionJob.user_id == user_id
        )
        if status:
            statement = statement.where(TranscriptionJob.status == status)
        result = self._session.exec(statement).one()
        return int(result[0]) if result else 0

    def list_assets(self, *, job_id: UUID, user_id: UUID) -> List[ScoreAsset]:
        """取得作業相關的輸出資產。"""

        statement = (
            select(ScoreAsset)
            .join(TranscriptionJob, ScoreAsset.job_id == TranscriptionJob.id)
            .where(
                ScoreAsset.job_id == job_id,
                TranscriptionJob.user_id == user_id,
            )
            .order_by(ScoreAsset.created_at.asc())
        )
        return self._session.exec(statement).all()
