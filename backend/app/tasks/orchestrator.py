"""轉譜任務 orchestrator 邏輯。"""
from __future__ import annotations

from typing import Any

from celery import Celery

from app.tasks.logging import emit_log


def process_transcription_job(app: Celery, job_id: str, payload: dict[str, Any]) -> None:
    """串接音訊準備、轉譜與發布流程。"""

    emit_log("process", f"啟動轉譜任務 job={job_id}")

    app.send_task(
        "app.tasks.ingest.ensure_audio",
        args=(job_id, payload.get("source_uri"), payload.get("storage_path")),
    )
    app.send_task(
        "app.tasks.process.transcribe_tracks",
        args=(job_id, payload.get("instrument_modes", []), "/tmp/audio.wav"),
    )
    app.send_task(
        "app.tasks.publish.publish_assets",
        args=(job_id, []),
    )
