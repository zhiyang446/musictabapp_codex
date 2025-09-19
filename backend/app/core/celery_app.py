"""Celery 應用初始化。"""
from __future__ import annotations

from celery import Celery

from app.core.config import settings
from app.tasks.utils import register_tasks


def create_celery_app() -> Celery:
    """建立 Celery 實例並載入設定。"""

    celery = Celery(
        "musictabapp",
        broker=settings.celery_broker_url or settings.redis_url,
        backend=settings.celery_result_url or settings.redis_url,
    )

    celery.conf.update(
        task_default_queue="transcription",
        task_acks_late=True,
        task_track_started=True,
        worker_max_tasks_per_child=100,
    )

    register_tasks(celery)

    return celery


celery_app: Celery = create_celery_app()
