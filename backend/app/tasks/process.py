"""轉譜流程任務邏輯。"""
from __future__ import annotations

from typing import List

from app.tasks.logging import emit_log


def transcribe_tracks(job_id: str, instrument_modes: List[str], audio_path: str) -> list[dict[str, str]]:
    """依樂器清單執行轉譜，回傳各樂器的輸出。"""

    emit_log("transcribe", f"開始轉譜 job={job_id}", instruments=instrument_modes)
    # TODO: 整合基本轉譜與 MIDI/MusicXML 生成
    outputs: list[dict[str, str]] = []
    for instrument in instrument_modes:
        outputs.append({
            "instrument": instrument,
            "midi_path": f"/tmp/{job_id}_{instrument}.midi",
            "musicxml_path": f"/tmp/{job_id}_{instrument}.musicxml",
        })
    return outputs
