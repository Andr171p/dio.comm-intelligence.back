import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus

import aiohttp

from .config import SrvIamConfig
from .dtos import Tokens

_TOKEN_REFRESH_MARGIN = 10


class SrvIamTokenProvider:
    """Выдаёт актуальный access токен сервисной учётки DIOS.

    Legacy: сервисных аккаунтов пока нет, service-to-service ходим под админом.
    """

    def __init__(self, config: SrvIamConfig) -> None:
        self._config = config
        self._session: aiohttp.ClientSession | None = None

        self._tokens: Tokens | None = None
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def _get_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout)
            self._session = aiohttp.ClientSession(base_url=str(self._config.base_url), timeout=timeout)

        yield self._session

    async def _login(self) -> Tokens:
        """Запрашивает пару токенов access + refresh."""

        if self._config.client_id is None or self._config.client_secret is None:
            raise RuntimeError("SRV_IAM_CLIENT_ID and SRV_IAM_CLIENT_SECRET are required.")

        payload = {
            "grant_type": "password",
            "username": self._config.client_id,
            "password": self._config.client_secret.get_secret_value(),
        }

        async with (
            self._get_session() as session,
            session.post("/api/v1/auth/login", data=payload) as response,
        ):
            response.raise_for_status()
            data = await response.json()

        return Tokens.model_validate(data)

    async def _refresh(self, tokens: Tokens) -> Tokens:
        """Получает новую пару токенов, при невалидном refresh токене логинится заново."""

        payload = {"refresh_token": tokens.refresh_token.get_secret_value()}

        try:
            async with (
                self._get_session() as session,
                session.post("/api/v1/auth/refresh", json=payload) as response,
            ):
                response.raise_for_status()
                data = await response.json()

        except aiohttp.ClientResponseError as exc:
            if exc.status in {HTTPStatus.UNAUTHORIZED, HTTPStatus.UNPROCESSABLE_ENTITY}:
                return await self._login()

            raise

        return Tokens.model_validate(data)

    async def get_token(self) -> str:
        """Возвращает актуальный access токен, обновляя его при необходимости."""

        async with self._lock:
            if self._tokens is None:
                self._tokens = await self._login()

            elif time.time() >= self._tokens.expires_at - _TOKEN_REFRESH_MARGIN:
                self._tokens = await self._refresh(self._tokens)

            return self._tokens.access_token.get_secret_value()

    async def close(self) -> None:
        if self._session is None or self._session.closed:
            return

        await self._session.close()
        self._session = None
