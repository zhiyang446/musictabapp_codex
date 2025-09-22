"""轉譯工作資料存取層。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlmodel import Session

from app.models.tables import JobEvent, ScoreAsset, TranscriptionJob


class JobRepository:
    """提供轉譯工作、事件與資產的資料操作介面。"""

    def __init__(self, session: Session) -> None:
        """使用既有的 Session 初始化儲存庫。"""

        self._session = session

    def create_job(self, job: TranscriptionJob) -> TranscriptionJob:
        """建立新的轉譯工作並回寫生成欄位。"""

        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def get_job(self, *, job_id: UUID, user_id: UUID) -> TranscriptionJob | None:
        """依使用者與工作 ID 取得單筆工作資料。"""

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
        """列出使用者的工作清單並依建立時間排序。"""

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
        """計算指定使用者（可選狀態）的工作總數。"""

        statement = select(func.count()).select_from(TranscriptionJob).where(
            TranscriptionJob.user_id == user_id
        )
        if status:
            statement = statement.where(TranscriptionJob.status == status)
        result = self._session.exec(statement).one()
        return int(result[0]) if result else 0

    def list_assets(self, *, job_id: UUID, user_id: UUID) -> List[ScoreAsset]:
        """列出指定工作下使用者可存取的譜面資產。"""

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

    def list_events(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
    ) -> List[JobEvent]:
        """列出使用者擁有之工作的時間軸事件。"""

        statement = (
            select(JobEvent)
            .join(TranscriptionJob, JobEvent.job_id == TranscriptionJob.id)
            .where(
                JobEvent.job_id == job_id,
                TranscriptionJob.user_id == user_id,
            )
            .order_by(JobEvent.created_at.asc())
        )
        return self._session.exec(statement).all()

    def count_jobs_by_statuses(self, *, user_id: UUID, statuses: Iterable[str]) -> int:
        """統計使用者在多個狀態下的工作數量。"""

        statuses = list(statuses)
        if not statuses:
            return 0
        statement = select(func.count()).select_from(TranscriptionJob).where(
            TranscriptionJob.user_id == user_id,
            TranscriptionJob.status.in_(statuses),
        )
        result = self._session.exec(statement).one()
        return int(result[0]) if result else 0

    def get_event(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        event_id: UUID,
    ) -> JobEvent | None:
        """依事件 ID 取得使用者所屬工作的單筆事件。"""

        statement = (
            select(JobEvent)
            .join(TranscriptionJob, JobEvent.job_id == TranscriptionJob.id)
            .where(
                JobEvent.id == event_id,
                JobEvent.job_id == job_id,
                TranscriptionJob.user_id == user_id,
            )
        )
        return self._session.exec(statement).first()

    def list_events_after(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        created_after: datetime | None = None,
        last_event_id: UUID | None = None,
    ) -> List[JobEvent]:
        """取得指定時間點後的事件清單，支援 Last-Event-ID 比對。"""

        statement = (
            select(JobEvent)
            .join(TranscriptionJob, JobEvent.job_id == TranscriptionJob.id)
            .where(
                JobEvent.job_id == job_id,
                TranscriptionJob.user_id == user_id,
            )
            .order_by(JobEvent.created_at.asc(), JobEvent.id.asc())
        )
        if created_after is not None:
            condition = JobEvent.created_at > created_after
            if last_event_id is not None:
                condition = or_(
                    JobEvent.created_at > created_after,
                    and_(
                        JobEvent.created_at == created_after,
                        JobEvent.id > last_event_id,
                    ),
                )
            statement = statement.where(condition)
        return self._session.exec(statement).all()
    def create_event(
        self,
        *,
        job_id: UUID,
        stage: str,
        message: str | None = None,
        payload: Dict[str, Any] | None = None,
    ) -> JobEvent:
        """新增一筆工作事件並立即持久化。"""

        event = JobEvent(
            job_id=job_id,
            stage=stage,
            message=message,
            payload=payload or {},
        )
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return event






