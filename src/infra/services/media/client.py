from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import UUID

import aiohttp

from .config import SrvMediaConfig
from .dtos import DownloadMediaDTO

_S3_CONNECT_TIMEOUT = 60


async def download_stream(url: str, chunk_size: int = 1024 * 64) -> AsyncIterable[bytes]:
    """Потоково скачивает файл из S3 по предподписанному URL."""

    timeout = aiohttp.ClientTimeout(connect=_S3_CONNECT_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session, session.get(url) as response:
        response.raise_for_status()

        async for chunk in response.content.iter_chunked(chunk_size):
            yield chunk


class SrvMediaClient:
    def __init__(self, config: SrvMediaConfig, get_token: Callable[[], Awaitable[str]]) -> None:
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

    async def create_download_url(self, media_id: UUID) -> DownloadMediaDTO:
        """Создаёт временный URL для скачивания объекта."""

        async with (
            self._get_token_session() as session,
            session.get(f"/api/v1/attachments/{media_id}/presigned-download") as response,
        ):
            response.raise_for_status()
            data = await response.json()

        return DownloadMediaDTO.model_validate(data)

    async def close(self) -> None:
        if self._session is None or self._session.closed:
            return

        await self._session.close()
        self._session = None
