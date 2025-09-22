"""/v1/jobs API endpoints."""
from __future__ import annotations

import asyncio
from datetime import datetime
import json
import time
from typing import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse, JSONResponse

from app.core.database import get_session
from app.core.security import require_current_user_id
from app.repositories.jobs import JobRepository
from app.models.tables import JobEvent
from app.schemas.asset import ScoreAssetListResponse, ScoreAssetResource
from app.schemas.event import JobEventListResponse, JobEventResource
from app.schemas.job import JobCreateRequest, JobListResponse, JobResource
from app.services.job_service import JobService, JobSubmissionLockedError

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_service(session=Depends(get_session)) -> JobService:
    """提供 FastAPI 相依性所需的 JobService 實例。"""

    repository = JobRepository(session)
    return JobService(repository)


@router.post(
    "",
    response_model=JobResource,
    status_code=status.HTTP_201_CREATED,
    summary="建立轉譯作業",
)
async def create_job(
    payload: JobCreateRequest,
    service: JobService = Depends(get_job_service),
    user_id: UUID = Depends(require_current_user_id),
) -> JobResource:
    """建立新的轉譯作業。"""

    try:
        job = service.create_job(payload=payload, user_id=user_id)
    except JobSubmissionLockedError as exc:
        detail = {"error": {"code": "JOB_SUBMISSION_LOCKED", "message": f"使用中作業數量 {exc.active} 已達上限"}}
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=detail) from exc
    return JobResource.model_validate(job)


@router.get("", response_model=JobListResponse, summary="查詢轉譯作業列表")
async def list_jobs(
    status: str | None = Query(default=None, description="依狀態篩選作業"),
    limit: int = Query(default=20, ge=1, le=100, description="回傳筆數上限"),
    offset: int = Query(default=0, ge=0, description="查詢位移"),
    service: JobService = Depends(get_job_service),
    user_id: UUID = Depends(require_current_user_id),
) -> JobListResponse:
    """依條件查詢使用者的轉譯作業。"""

    jobs, total = service.list_jobs(user_id=user_id, status=status, limit=limit, offset=offset)
    items = [JobResource.model_validate(job) for job in jobs]
    return JobListResponse(data=items, total=total)


@router.get("/{job_id}", response_model=JobResource, summary="取得轉譯作業詳情")
async def retrieve_job(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
    user_id: UUID = Depends(require_current_user_id),
) -> JobResource:
    """取得指定轉譯作業的詳細資訊。"""

    job = service.get_job(user_id=user_id, job_id=job_id)
    if job is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found"}},
        )

    return JobResource.model_validate(job)


@router.get(
    "/{job_id}/assets",
    response_model=ScoreAssetListResponse,
    summary="查詢作業產出的譜面資產",
)
async def list_job_assets(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
    user_id: UUID = Depends(require_current_user_id),
) -> ScoreAssetListResponse:
    """取得作業產出的譜面資產列表。"""

    assets = service.list_job_assets(user_id=user_id, job_id=job_id)
    if assets is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    items = [ScoreAssetResource.model_validate(asset) for asset in assets]
    return ScoreAssetListResponse(data=items)


@router.get(
    "/{job_id}/events",
    response_model=JobEventListResponse,
    summary="查詢作業事件時間軸",
)
async def list_job_events(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
    user_id: UUID = Depends(require_current_user_id),
) -> JobEventListResponse:
    """取得作業事件時間軸。"""

    events = service.list_job_events(user_id=user_id, job_id=job_id)
    if events is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    items = [JobEventResource.model_validate(event) for event in events]
    return JobEventListResponse(data=items)


@router.get(
    "/{job_id}/stream",
    summary="SSE 串流作業事件",
)
async def stream_job_events(
    job_id: UUID,
    request: Request,
    service: JobService = Depends(get_job_service),
    user_id: UUID = Depends(require_current_user_id),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """以 SSE 持續串流指定作業的事件。"""

    job = service.get_job(user_id=user_id, job_id=job_id)
    if job is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found"}},
        )

    last_event_uuid: UUID | None = None  # 最後一次送出的事件 ID，用於去重補齊
    last_created_at: datetime | None = None  # 最後一次送出的事件時間戳
    if last_event_id:
        try:
            last_event_uuid = UUID(last_event_id)
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": {"code": "INVALID_LAST_EVENT_ID", "message": "Last-Event-ID 必須為 UUID"}},
            )

        matched_event = service.get_job_event(user_id=user_id, job_id=job_id, event_id=last_event_uuid)
        if matched_event is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": {"code": "INVALID_LAST_EVENT_ID", "message": "Last-Event-ID 不存在或不屬於該任務"}},
            )
        last_created_at = matched_event.created_at

    poll_interval = 1.0  # 每 1 秒輪詢一次事件表
    heartbeat_interval = 30.0  # 每 30 秒送出一次 keep-alive
    heartbeat_payload = b":keep-alive\n\n"  # SSE 心跳訊號，保持連線
    last_sent_monotonic = time.monotonic()  # 紀錄最近一次輸出的時間戳

    def serialize_event(event: JobEvent) -> bytes:
        """將事件轉換為 SSE 格式的位元組資料。"""

        resource = JobEventResource.model_validate(event)
        payload = json.dumps(resource.model_dump(by_alias=True, mode="json"), ensure_ascii=False)
        lines = [f"id:{event.id}", f"event:{resource.stage}", f"data:{payload}", ""]
        return "\n".join(lines).encode("utf-8")

    async def event_source() -> AsyncGenerator[bytes, None]:
        """產生 SSE 串流資料。"""

        nonlocal last_event_uuid, last_created_at, last_sent_monotonic

        initial_events = service.list_job_events_after(
            user_id=user_id,
            job_id=job_id,
            created_after=last_created_at,
            last_event_id=last_event_uuid,
        )
        for event in initial_events:
            last_event_uuid = event.id
            last_created_at = event.created_at
            last_sent_monotonic = time.monotonic()
            yield serialize_event(event)

        while True:
            if await request.is_disconnected():
                break

            new_events = service.list_job_events_after(
                user_id=user_id,
                job_id=job_id,
                created_after=last_created_at,
                last_event_id=last_event_uuid,
            )
            if new_events:
                for event in new_events:
                    last_event_uuid = event.id
                    last_created_at = event.created_at
                    last_sent_monotonic = time.monotonic()
                    yield serialize_event(event)
            else:
                now = time.monotonic()
                if now - last_sent_monotonic >= heartbeat_interval:
                    last_sent_monotonic = now
                    yield heartbeat_payload

            await asyncio.sleep(poll_interval)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_source(), media_type="text/event-stream", headers=headers)
