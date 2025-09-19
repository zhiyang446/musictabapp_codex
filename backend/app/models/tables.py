"""SQLModel 資料表定義。"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, Index, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    """產生帶有 UTC 時區資訊的當前時間。"""

    return datetime.now(timezone.utc)


class SourceType(str, Enum):
    """作業來源型態定義。"""

    LOCAL = "local"
    YOUTUBE = "youtube"


class JobStatus(str, Enum):
    """轉譜作業的狀態列舉。"""

    PENDING = "pending"
    PROCESSING = "processing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoreFormat(str, Enum):
    """譜面資產輸出格式。"""

    MIDI = "midi"
    MUSICXML = "musicxml"
    PDF = "pdf"


class PresetVisibility(str, Enum):
    """預設組態的可見性設定。"""

    PUBLIC = "public"
    PRIVATE = "private"


class Profile(SQLModel, table=True):
    """使用者個人資料表。"""

    __tablename__ = "profiles"

    user_id: UUID = Field(primary_key=True, foreign_key="auth.users.id", description="對應 Supabase 使用者 ID")
    display_name: Optional[str] = Field(default=None, description="顯示名稱")
    avatar_url: Optional[str] = Field(default=None, description="頭像連結")
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=_utc_now,
        description="建立時間",
    )

    __table_args__ = (Index("ix_profiles_created_at", "created_at"),)


class TranscriptionJob(SQLModel, table=True):
    """轉譜作業主檔。"""

    __tablename__ = "transcription_jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True, description="作業主鍵")
    user_id: UUID = Field(foreign_key="auth.users.id", index=True, description="建立作業的使用者")
    source_type: SourceType = Field(
        sa_column=Column(SAEnum(SourceType, name="source_type_enum", native_enum=False), nullable=False),
        description="來源類型",
    )
    source_uri: Optional[str] = Field(default=None, description="來源原始位置 (YouTube URL 或檔案連結)")
    storage_object_path: Optional[str] = Field(default=None, description="Supabase Storage 物件路徑")
    instrument_modes: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, server_default=text("'[]'::jsonb")),
        description="欲產出之樂器清單",
    )
    model_profile: str = Field(default="balanced", description="使用的模型設定檔")
    status: JobStatus = Field(
        default=JobStatus.PENDING,
        sa_column=Column(SAEnum(JobStatus, name="job_status_enum", native_enum=False), nullable=False),
        description="作業狀態",
    )
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="進度百分比")
    error_message: Optional[str] = Field(default=None, description="失敗訊息")
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=_utc_now,
        description="建立時間",
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        default_factory=_utc_now,
        description="更新時間",
    )

    __table_args__ = (
        Index("ix_transcription_jobs_status", "status"),
        Index("ix_transcription_jobs_created_at", "created_at"),
    )


class JobEvent(SQLModel, table=True):
    """作業事件時間軸。"""

    __tablename__ = "job_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True, description="事件主鍵")
    job_id: UUID = Field(foreign_key="transcription_jobs.id", description="關聯的作業 ID")
    stage: str = Field(description="所處階段代碼")
    message: Optional[str] = Field(default=None, description="事件訊息")
    payload: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="附加資料",
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=_utc_now,
        description="記錄時間",
    )

    __table_args__ = (Index("ix_job_events_job_id_created_at", "job_id", "created_at"),)


class ScoreAsset(SQLModel, table=True):
    """譜面輸出資產表。"""

    __tablename__ = "score_assets"

    id: UUID = Field(default_factory=uuid4, primary_key=True, description="資產主鍵")
    job_id: UUID = Field(foreign_key="transcription_jobs.id", index=True, description="所屬作業")
    instrument: str = Field(description="樂器分類")
    format: ScoreFormat = Field(
        sa_column=Column(SAEnum(ScoreFormat, name="score_format_enum", native_enum=False), nullable=False),
        description="輸出格式",
    )
    storage_object_path: str = Field(description="Supabase Storage 物件路徑")
    duration_seconds: Optional[int] = Field(default=None, ge=0, description="音軌長度 (秒)")
    page_count: Optional[int] = Field(default=None, ge=0, description="PDF 頁數")
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=_utc_now,
        description="建立時間",
    )

    __table_args__ = (
        UniqueConstraint("job_id", "instrument", "format", name="uq_score_assets_job_instrument_format"),
    )


class ProcessingMetric(SQLModel, table=True):
    """作業性能指標記錄。"""

    __tablename__ = "processing_metrics"

    id: UUID = Field(default_factory=uuid4, primary_key=True, description="指標主鍵")
    job_id: UUID = Field(foreign_key="transcription_jobs.id", index=True, description="關聯作業")
    latency_ms: Optional[int] = Field(default=None, ge=0, description="總延遲 (毫秒)")
    cpu_usage: Optional[float] = Field(default=None, ge=0.0, description="CPU 使用量")
    memory_mb: Optional[float] = Field(default=None, ge=0.0, description="記憶體使用量")
    model_versions: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="模型版本資訊",
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=_utc_now,
        description="建立時間",
    )


class Preset(SQLModel, table=True):
    """使用者或系統預設的樂器組態。"""

    __tablename__ = "presets"

    id: UUID = Field(default_factory=uuid4, primary_key=True, description="預設主鍵")
    user_id: Optional[UUID] = Field(
        default=None,
        foreign_key="auth.users.id",
        description="擁有者；為空代表公開預設",
    )
    name: str = Field(description="預設名稱")
    description: Optional[str] = Field(default=None, description="描述")
    instrument_modes: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, server_default=text("'[]'::jsonb")),
        description="預設樂器列表",
    )
    tempo_hint: Optional[int] = Field(default=None, ge=0, description="建議節奏")
    visibility: PresetVisibility = Field(
        default=PresetVisibility.PRIVATE,
        sa_column=Column(SAEnum(PresetVisibility, name="preset_visibility_enum", native_enum=False), nullable=False),
        description="可見性",
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=_utc_now,
        description="建立時間",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_presets_user_name"),
        Index("ix_presets_user_id", "user_id"),
        Index("ix_presets_public_name", "name", unique=True, postgresql_where=text("user_id IS NULL")),
    )
