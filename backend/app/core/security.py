"""使用者驗證相關工具。"""
from __future__ import annotations

import time
from typing import Dict
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from app.core.config import settings

WWW_AUTH_HEADER = {"WWW-Authenticate": "Bearer"}
TOKEN_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or missing authorization token",
    headers=WWW_AUTH_HEADER,
)


class JWKSProvider:
    """簡易 JWKS 客戶端，提供快取以減少遠端請求。"""

    def __init__(self, url: str, cache_seconds: int = 300) -> None:
        if not url:
            raise ValueError("SUPABASE_JWKS_URL 未設定")
        self._url = url
        self._cache_seconds = cache_seconds
        self._keys: Dict[str, dict] = {}
        self._expires_at: float = 0.0

    async def get_signing_key(self, kid: str) -> dict:
        """根據 kid 取得對應的 JWK。"""

        await self._ensure_keys()
        key = self._keys.get(kid)
        if key is not None:
            return key
        self._keys.clear()
        self._expires_at = 0.0
        await self._ensure_keys()
        key = self._keys.get(kid)
        if key is None:
            raise TOKEN_ERROR
        return key

    async def _ensure_keys(self) -> None:
        if self._keys and time.time() < self._expires_at:
            return
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self._url)
                response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            self._keys.clear()
            self._expires_at = 0.0
            raise TOKEN_ERROR from exc

        jwks = payload.get("keys", [])
        if not isinstance(jwks, list):
            self._keys.clear()
            self._expires_at = 0.0
            raise TOKEN_ERROR

        keys = {
            item["kid"]: item
            for item in jwks
            if isinstance(item, dict) and "kid" in item
        }
        if not keys:
            self._keys.clear()
            self._expires_at = 0.0
            raise TOKEN_ERROR

        self._keys = keys
        self._expires_at = time.time() + self._cache_seconds


_jwks_provider = JWKSProvider(settings.supabase_jwks_url or "")


def get_supabase_issuer() -> str:
    """取得 Supabase JWT 的 issuer。"""

    issuer = settings.supabase_jwt_issuer
    if issuer:
        return issuer
    if settings.supabase_jwks_url:
        return settings.supabase_jwks_url.replace("/certs", "")
    raise ValueError("Supabase issuer 未設定")


def get_supabase_audience() -> str | list[str]:
    """整理 Supabase JWT 的 audience 設定。"""

    raw = settings.supabase_jwt_audience
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("Supabase audience 未設定")
    return values if len(values) > 1 else values[0]


async def get_current_user_id(request: Request) -> UUID:
    """解析 JWT 並回傳當前使用者 ID。"""

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise TOKEN_ERROR

    token = auth_header.split(" ", 1)[1].strip()
    try:
        unverified = jwt.get_unverified_header(token)
    except JWTError as exc:  # pragma: no cover - jose 已涵蓋
        raise TOKEN_ERROR from exc

    kid = unverified.get("kid")
    if not kid:
        raise TOKEN_ERROR

    key = await _jwks_provider.get_signing_key(kid)
    algorithm = unverified.get("alg", "RS256")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=get_supabase_audience(),
            issuer=get_supabase_issuer(),
        )
    except JWTError as exc:  # pragma: no cover - jose 已涵蓋
        raise TOKEN_ERROR from exc

    subject = claims.get("sub")
    if not subject:
        raise TOKEN_ERROR

    try:
        return UUID(subject)
    except ValueError as exc:
        raise TOKEN_ERROR from exc


async def require_current_user_id(request: Request) -> UUID:
    """FastAPI 依賴別名，供路由使用。"""

    return await get_current_user_id(request)
