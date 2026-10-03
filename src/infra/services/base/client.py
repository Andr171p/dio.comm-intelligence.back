import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus

import aiohttp
from pydantic import BaseModel, Field, PositiveInt, SecretStr

from .config import SrvBaseConfig


class _Tokens(BaseModel):
    access_token: SecretStr = Field(description="Короткоживущий токен")
    refresh_token: SecretStr = Field(description="Долгоживущий токен (для получения новой пары)")
    expires_at: PositiveInt = Field(description="Время истечения в timestamp")


class SrvBaseClient:
    def __init__(self, config: SrvBaseConfig) -> None:
        self._config = config
        self._session: aiohttp.ClientSession | None = None

        self._tokens: _Tokens | None = None
        self._tokens_lock = asyncio.Lock()

    @asynccontextmanager
    async def _get_token_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        async with self.__get_session() as session:
            access_token = await self.__get_access_token()
            session.headers["Authorization"] = f"Bearer {access_token}"
            yield session

    @asynccontextmanager
    async def __get_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout)
            self._session = aiohttp.ClientSession(base_url=str(self._config.base_url), timeout=timeout)

        yield self._session

    def __auth_endpoint(self, action: str) -> str:
        """Абсолютный URL эндпоинта IAM (aiohttp не склеивает абсолютные URL с base_url сессии)."""

        auth_url = str(self._config.auth_url or self._config.base_url).rstrip("/")
        return f"{auth_url}/api/v1/auth/{action}"

    async def __authenticate(self) -> _Tokens:
        """Запрашивает пару токенов access + refresh."""

        payload: dict[str, str] = {
            "grant_type": "password",
            "username": self._config.client_id,
            "password": self._config.client_secret.get_secret_value(),
        }

        async with (
            self.__get_session() as session,
            session.post(self.__auth_endpoint("login"), data=payload) as response,
        ):
            response.raise_for_status()
            data = await response.json()

        return _Tokens.model_validate(data)

    async def __refresh_tokens(self) -> _Tokens:
        """Получает новую пару access + refresh, при невалидном refresh аутентифицируется заново."""

        payload: dict[str, str] = {"refresh_token": self._tokens.refresh_token.get_secret_value()}

        try:
            async with (
                self.__get_session() as session,
                session.post(self.__auth_endpoint("refresh"), json=payload) as response,
            ):
                response.raise_for_status()
                data = await response.json()

        except aiohttp.ClientResponseError as exc:
            if exc.status in {HTTPStatus.UNAUTHORIZED, HTTPStatus.UNPROCESSABLE_ENTITY}:
                return await self.__authenticate()

            raise

        return _Tokens.model_validate(data)

    async def __get_access_token(self) -> str:
        """Потокобезопасно получает актуальный access токен."""

        async with self._tokens_lock:
            if self._tokens is None:
                self._tokens = await self.__authenticate()

            elif time.time() >= self._tokens.expires_at - self._config.token_refresh_margin:
                self._tokens = await self.__refresh_tokens()

            return self._tokens.access_token.get_secret_value()

    async def close(self) -> None:
        """Безопасное закрытие сессии."""

        if self._session is None or self._session.closed:
            return

        await self._session.close()
        self._session = None
