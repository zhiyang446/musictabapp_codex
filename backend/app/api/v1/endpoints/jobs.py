"""/v1/jobs API endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import get_session
from app.core.security import require_current_user_id
from app.repositories.jobs import JobRepository
from app.schemas.asset import ScoreAssetListResponse, ScoreAssetResource
from app.schemas.job import JobCreateRequest, JobListResponse, JobResource
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_service(session=Depends(get_session)) -> JobService:
    """FastAPI 依賴：組裝 JobService。"""

    repository = JobRepository(session)
    return JobService(repository)


@router.post(
    "",
    response_model=JobResource,
    status_code=status.HTTP_201_CREATED,
    summary="建立新的轉譜作業",
)
async def create_job(
    payload: JobCreateRequest,
    service: JobService = Depends(get_job_service),
    user_id: UUID = Depends(require_current_user_id),
) -> JobResource:
    """建立作業並立即回傳作業資源。"""

    job = service.create_job(payload=payload, user_id=user_id)
    return JobResource.model_validate(job)


@router.get("", response_model=JobListResponse, summary="取得作業列表")
async def list_jobs(
    status: str | None = Query(default=None, description="依狀態過濾作業"),
    limit: int = Query(default=20, ge=1, le=100, description="一次取回的數量"),
    offset: int = Query(default=0, ge=0, description="起始偏移量"),
    service: JobService = Depends(get_job_service),
    user_id: UUID = Depends(require_current_user_id),
) -> JobListResponse:
    """回傳作業清單以及總筆數。"""

    jobs, total = service.list_jobs(user_id=user_id, status=status, limit=limit, offset=offset)
    items = [JobResource.model_validate(job) for job in jobs]
    return JobListResponse(data=items, total=total)


@router.get("/{job_id}", response_model=JobResource, summary="取得作業詳情")
async def retrieve_job(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
    user_id: UUID = Depends(require_current_user_id),
) -> JobResource:
    """回傳指定作業的詳細資訊。"""

    job = service.get_job(user_id=user_id, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResource.model_validate(job)


@router.get(
    "/{job_id}/assets",
    response_model=ScoreAssetListResponse,
    summary="取得作業資產列表",
)
async def list_job_assets(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
    user_id: UUID = Depends(require_current_user_id),
) -> ScoreAssetListResponse:
    """列出指定作業的資產清單。"""

    assets = service.list_job_assets(user_id=user_id, job_id=job_id)
    if assets is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    items = [ScoreAssetResource.model_validate(asset) for asset in assets]
    return ScoreAssetListResponse(data=items)
