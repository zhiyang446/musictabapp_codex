"""健康檢查相關測試。"""
from fastapi.testclient import TestClient

from app.main import create_app


def test_read_health() -> None:
    """確認健康檢查端點回傳成功狀態。"""

    # client 用於模擬 API 呼叫
    client = TestClient(create_app())

    response = client.get("/v1/system/health")
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["service"]
