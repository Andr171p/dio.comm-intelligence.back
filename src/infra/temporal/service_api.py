from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import UUID

import aiohttp
from pydantic import Field, HttpUrl, PositiveFloat
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.application.communications.dtos import CommunicationResponse, UpdateCommunicationDTO


class ServiceApiConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SERVICE_API_")

    base_url: HttpUrl = Field(description="URL API этого сервиса")
    timeout: PositiveFloat = Field(default=60, description="Таймаут в секундах")


class ServiceApiClient:
    """Клиент `/api/service/v1`: activities работают с данными только через API сервиса."""

    def __init__(self, config: ServiceApiConfig, get_token: Callable[[], Awaitable[str]]) -> None:
        self._config = config
        self._get_token = get_token
        self._session: aiohttp.ClientSession | None = None

    @asynccontextmanager
    async def _get_token_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout)
            self._session = aiohttp.ClientSession(base_url=str(self._config.base_url), timeout=timeout)

        self._session.headers["Authorization"] = f"Bearer {await self._get_token()}"
        yield self._session

    async def get_communication(self, communication_id: UUID) -> CommunicationResponse:
        async with (
            self._get_token_session() as session,
            session.get(f"/api/service/v1/communications/{communication_id}") as response,
        ):
            response.raise_for_status()
            data = await response.text()

        return CommunicationResponse.model_validate_json(data)

    async def update_communication(
        self, communication_id: UUID, dto: UpdateCommunicationDTO,
    ) -> CommunicationResponse:
        payload = dto.model_dump(mode="json", by_alias=True, exclude_unset=True)

        async with (
            self._get_token_session() as session,
            session.patch(f"/api/service/v1/communications/{communication_id}", json=payload) as response,
        ):
            response.raise_for_status()
            data = await response.text()

        return CommunicationResponse.model_validate_json(data)

    async def close(self) -> None:
        if self._session is None or self._session.closed:
            return

        await self._session.close()
        self._session = None


__all__ = ["ServiceApiClient", "ServiceApiConfig"]
