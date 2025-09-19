"""成果發布與通知任務邏輯。"""
from __future__ import annotations

from typing import Iterable

from app.tasks.logging import emit_log


def publish_assets(job_id: str, artifacts: Iterable[dict[str, str]]) -> None:
    """將轉譜成果上傳儲存並通知使用者。"""

    emit_log("publish", f"發布譜面資產 job={job_id}")
    for artifact in artifacts:
        emit_log("publish", "資產資訊", instrument=artifact.get("instrument"))
    # TODO: 寫入 score_assets、觸發通知
