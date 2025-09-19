"""Celery 任務共用工具。"""
from __future__ import annotations

from typing import Any

from celery import Celery
from loguru import logger

from app.tasks import ingest, orchestrator, process, publish


def register_tasks(celery: Celery) -> None:
    """將任務邏輯註冊到 Celery 應用。"""

    celery.task(name="app.tasks.ingest.ensure_audio")(ingest.ensure_audio)
    celery.task(name="app.tasks.process.transcribe_tracks")(process.transcribe_tracks)
    celery.task(name="app.tasks.publish.publish_assets")(publish.publish_assets)

    @celery.task(
        name="app.tasks.orchestrator.process_transcription_job",
        bind=True,
        autoretry_for=(Exception,),
        retry_backoff=True,
    )
    def process_transcription_job_task(self, job_id: str, payload: dict[str, Any]) -> None:
        orchestrator.process_transcription_job(self.app, job_id, payload)

    logger.debug("Registered Celery tasks: {}", list(celery.tasks.keys()))
