"""轉譜作業的資料存取層。"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlmodel import Session

from app.models.tables import TranscriptionJob


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

    def list_jobs(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[TranscriptionJob]:
        """依條件取得作業列表。"""

        statement = select(TranscriptionJob).order_by(TranscriptionJob.created_at.desc())
        if status:
            statement = statement.where(TranscriptionJob.status == status)
        statement = statement.offset(offset).limit(limit)
        result = self._session.execute(statement)
        return [row[0] for row in result]

    def count_jobs(self, *, status: Optional[str] = None) -> int:
        """計算作業總量，用於分頁。"""

        statement = select(func.count()).select_from(TranscriptionJob)
        if status:
            statement = statement.where(TranscriptionJob.status == status)
        return self._session.execute(statement).scalar_one()
