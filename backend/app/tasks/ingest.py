"""音訊來源處理任務邏輯。"""
from __future__ import annotations

from app.tasks.logging import emit_log


def ensure_audio(job_id: str, source_uri: str | None, storage_path: str | None) -> dict[str, str | None]:
    """準備音訊檔（下載或確認上傳完成）。"""

    emit_log("audio_ingest", f"準備音訊資源 job={job_id}")
    # TODO: 實作下載/檔案檢查邏輯
    return {"local_path": "path/to/audio.wav", "storage_path": storage_path}
