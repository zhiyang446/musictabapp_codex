"""Celery 設定測試。"""
from celery import Celery

from app.core.celery_app import create_celery_app


def test_create_celery_app() -> None:
    """驗證 Celery 應用初始化成功且載入任務模組。"""

    celery: Celery = create_celery_app()

    assert celery.main == "musictabapp"

    task_names = set(celery.tasks.keys())
    expected_tasks = {
        "app.tasks.ingest.ensure_audio",
        "app.tasks.process.transcribe_tracks",
        "app.tasks.publish.publish_assets",
        "app.tasks.orchestrator.process_transcription_job",
    }

    assert expected_tasks.issubset(task_names)
