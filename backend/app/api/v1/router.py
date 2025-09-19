"""API v1 路由聚合。"""
from fastapi import APIRouter

from app.api.v1.endpoints import health, jobs

# api_router 用於收斂所有 v1 子路由
api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(jobs.router)
