"""應用進入點。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    """建立 FastAPI 主應用並綁定路由與中介層。"""

    app = FastAPI(title=settings.project_name)

    # 設定 CORS 允許前端應用存取 API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


# app 供 ASGI 伺服器載入執行
app: FastAPI = create_app()
