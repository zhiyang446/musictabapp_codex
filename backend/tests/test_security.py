import os
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi import HTTPException, Request
from jose import jwt
from jose.utils import base64url_encode
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# 確保載入安全模組前已設定 JWKS URL
os.environ.setdefault("SUPABASE_JWKS_URL", "https://example.supabase.co/auth/v1/certs")

from app.core import security  # noqa: E402
from app.core.security import TOKEN_ERROR  # noqa: E402

TEST_USER_ID = "00000000-0000-0000-0000-000000000123"


def _generate_test_key_material() -> tuple[str, dict[str, Any]]:
    """產生測試用的 RSA 金鑰與對應 JWK。"""

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_numbers = private_key.public_key().public_numbers()
    n_bytes = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")
    e_bytes = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")

    jwk = {
        "kty": "RSA",
        "kid": "test-key",
        "alg": "RS256",
        "use": "sig",
        "n": base64url_encode(n_bytes).decode(),
        "e": base64url_encode(e_bytes).decode(),
    }
    return private_pem, jwk


TEST_PRIVATE_KEY, TEST_JWK = _generate_test_key_material()


class StubJWKSProvider:
    """提供固定 JWK 的替身實作。"""

    def __init__(self, jwk: dict[str, Any]) -> None:
        self._jwk = jwk
        self.calls = 0  # 呼叫次數統計

    async def get_signing_key(self, kid: str) -> dict[str, Any]:
        """回傳對應 kid 的 JWK，若不符則拋出 TOKEN_ERROR。"""

        self.calls += 1
        if kid != self._jwk["kid"]:
            raise TOKEN_ERROR
        return self._jwk


def _build_request(token: str | None) -> Request:
    """建立附帶 Authorization Header 的 Request。"""

    headers = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_get_current_user_id_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """驗證合法 JWT 會解析出使用者 UUID。"""

    provider = StubJWKSProvider(TEST_JWK)
    monkeypatch.setattr(security, "_jwks_provider", provider, raising=False)
    monkeypatch.setattr(security.settings, "supabase_jwt_audience", "test-aud")
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", "https://example.supabase.co/auth/v1")

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": TEST_USER_ID,
            "aud": "test-aud",
            "iss": "https://example.supabase.co/auth/v1",
            "exp": now + timedelta(minutes=5),
        },
        TEST_PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": TEST_JWK["kid"]},
    )

    request = _build_request(token)
    user_id = await security.get_current_user_id(request)

    assert str(user_id) == TEST_USER_ID
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_get_current_user_id_missing_header() -> None:
    """缺少 Authorization Header 時回傳 401。"""

    request = _build_request(None)
    with pytest.raises(HTTPException) as exc:
        await security.get_current_user_id(request)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_id_invalid_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    """JWT sub 非 UUID 時應失敗。"""

    provider = StubJWKSProvider(TEST_JWK)
    monkeypatch.setattr(security, "_jwks_provider", provider, raising=False)
    monkeypatch.setattr(security.settings, "supabase_jwt_audience", "test-aud")
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", "https://example.supabase.co/auth/v1")

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "not-a-uuid",
            "aud": "test-aud",
            "iss": "https://example.supabase.co/auth/v1",
            "exp": now + timedelta(minutes=5),
        },
        TEST_PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": TEST_JWK["kid"]},
    )

    request = _build_request(token)
    with pytest.raises(HTTPException) as exc:
        await security.get_current_user_id(request)
    assert exc.value.status_code == 401


def test_get_supabase_audience_supports_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    """設定多個 audience 時會拆解為清單。"""

    monkeypatch.setattr(security.settings, "supabase_jwt_audience", "authenticated, service_role ")
    assert security.get_supabase_audience() == ["authenticated", "service_role"]


def test_get_supabase_audience_single(monkeypatch: pytest.MonkeyPatch) -> None:
    """單一 audience 則維持字串輸出。"""

    monkeypatch.setattr(security.settings, "supabase_jwt_audience", "authenticated")
    assert security.get_supabase_audience() == "authenticated"
