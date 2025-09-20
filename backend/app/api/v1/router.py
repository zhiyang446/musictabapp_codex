"""API v1 路由設定。"""
from fastapi import APIRouter

from app.api.v1.endpoints import health, jobs, uploads

# api_router 負責收攏 v1 版本的所有路由
api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(jobs.router)
api_router.include_router(uploads.router)

