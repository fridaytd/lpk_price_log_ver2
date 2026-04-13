import asyncio
import logging
import time
from typing import Final

import httpx
import jwt  # PyJWT

logger = logging.getLogger(__name__)

SCOPES: Final[str] = "https://www.googleapis.com/auth/spreadsheets"
TOKEN_URL: Final[str] = "https://oauth2.googleapis.com/token"
GRANT_TYPE: Final[str] = "urn:ietf:params:oauth:grant-type:jwt-bearer"
TOKEN_LIFETIME: Final[int] = 3600   # seconds; Google's standard token TTL
REFRESH_BUFFER: Final[int] = 60     # refresh when < 60 s remain


class TokenCache:
    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}          # filename → {"token": str, "expires_at": float}
        self._locks: dict[str, asyncio.Lock] = {}  # filename → asyncio.Lock

    async def get_token(self, filename: str, key_data: dict) -> str:
        # Fast path — valid cached token
        entry = self._cache.get(filename)
        if entry and time.time() < entry["expires_at"] - REFRESH_BUFFER:
            return entry["token"]

        # Slow path — acquire per-key lock, then double-check
        lock = self._locks.setdefault(filename, asyncio.Lock())
        async with lock:
            entry = self._cache.get(filename)  # re-check after acquiring lock
            if entry and time.time() < entry["expires_at"] - REFRESH_BUFFER:
                return entry["token"]  # another coroutine already refreshed

            token, expires_at = await self._fetch_token(filename, key_data)
            self._cache[filename] = {"token": token, "expires_at": expires_at}
            return token

    async def _fetch_token(self, filename: str, key_data: dict) -> tuple[str, float]:
        now = int(time.time())
        payload = {
            "iss": key_data["client_email"],
            "scope": SCOPES,
            "aud": TOKEN_URL,
            "iat": now,
            "exp": now + TOKEN_LIFETIME,
        }
        assertion = jwt.encode(payload, key_data["private_key"], algorithm="RS256")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                data={"grant_type": GRANT_TYPE, "assertion": assertion},
            )
            resp.raise_for_status()
            data = resp.json()

        access_token: str = data["access_token"]
        expires_in: int = data.get("expires_in", TOKEN_LIFETIME)
        expires_at = time.time() + expires_in

        logger.debug(f"TokenCache: fetched new token for key: {filename}")  # filename ONLY — never token content
        return access_token, expires_at
