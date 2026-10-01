import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from uuid import UUID

import aiohttp

from .config import SrvMediaConfig
from .dtos import DownloadMediaDTO, Tokens

_TOKEN_REFRESH_MARGIN = 10


class SrvMediaClient:
    def __init__(self, config: SrvMediaConfig) -> None:
        self._config = config
        self._session: aiohttp.ClientSession | None = None

        self._tokens: Tokens | None = None

    async def _authenticate(self, session: aiohttp.ClientSession) -> Tokens:
        """Запрашивает пару токенов access + refresh."""

        payload = {
            "grant_type": "password",
            "username": self._config.client_id,
            "password": self._config.client_secret,
        }

        async with session.post("/api/v1/auth/login", data=payload) as response:
            response.raise_for_status()
            data = response.json()

        self._tokens = Tokens.model_validate(data)
        return self._tokens

    async def _refresh_tokens(self, session: aiohttp.ClientSession) -> Tokens:
        """Получает новую пару токенов."""

        if not self._tokens:
            return await self._authenticate(session)

        payload = {"refresh_token": self._tokens.refresh_token.get_secret_value()}

        try:
            async with session.post("/api/v1/auth/refresh", data=payload) as response:
                response.raise_for_status()
                data = await response.json()

            self._tokens = Tokens.model_validate(data)
            return self._tokens

        except aiohttp.ClientResponseError as exc:
            if exc.status in {HTTPStatus.UNAUTHORIZED, HTTPStatus.UNPROCESSABLE_ENTITY}:
                return await self._authenticate(session)

            raise exc

    async def _get_valid_token(self, session: aiohttp.ClientSession) -> str:
        """Возвращает актуальный Access токен, обновляя его при необходимости."""

        if not self._tokens:
            tokens = await self._authenticate(session)
            return tokens.access_token.get_secret_value()

        if time.time() >= self._tokens.expires_at - _TOKEN_REFRESH_MARGIN:
            tokens = await self._refresh_tokens(session)
            return tokens.access_token.get_secret_value()

        return self._tokens.access_token.get_secret_value()

    @asynccontextmanager
    async def _get_token_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout)
            self._session = aiohttp.ClientSession(base_url=str(self._config.base_url), timeout=timeout)

        token = await self._get_valid_token(self._session)
        self._session.headers["Authorization"] = f"Bearer {token}"
        yield self._session

    async def create_download_url(self, media_id: UUID) -> DownloadMediaDTO:
        """Создаёт временный URL для скачивания объекта."""

        async with (
            self._get_token_session() as session,
            session.get(f"/api/v1/attachments/{media_id}/presigned-download") as response,
        ):
            response.raise_for_status()
            data = await response.json()

        return DownloadMediaDTO.model_validate(data)
