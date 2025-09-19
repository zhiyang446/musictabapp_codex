"""資料模型定義測試。"""
from sqlmodel import SQLModel

from app import models  # noqa: F401 確保模型載入


def test_tables_and_columns_defined() -> None:
    """確認核心資料表及關鍵欄位皆已透過 SQLModel 定義。"""

    # table_map 儲存所有註冊的資料表
    table_map = SQLModel.metadata.tables

    expected_tables = {
        "profiles",
        "transcription_jobs",
        "job_events",
        "score_assets",
        "processing_metrics",
        "presets",
    }
    assert expected_tables.issubset(set(table_map.keys()))

    expected_columns = {
        "profiles": {"user_id", "display_name", "avatar_url", "created_at"},
        "transcription_jobs": {
            "id",
            "user_id",
            "source_type",
            "instrument_modes",
            "status",
            "progress",
            "created_at",
            "updated_at",
        },
        "job_events": {"id", "job_id", "stage", "payload", "created_at"},
        "score_assets": {"id", "job_id", "instrument", "format", "storage_object_path"},
        "processing_metrics": {"id", "job_id", "latency_ms", "created_at"},
        "presets": {"id", "user_id", "name", "visibility", "instrument_modes"},
    }

    for table_name, columns in expected_columns.items():
        column_names = set(table_map[table_name].c.keys())
        assert columns.issubset(column_names)

    # 驗證 score_assets 的唯一鍵確保樂器與格式不重複
    score_assets_constraints = {
        constraint.name for constraint in table_map["score_assets"].constraints if constraint.name
    }
    assert "uq_score_assets_job_instrument_format" in score_assets_constraints
