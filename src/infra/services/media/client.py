from collections.abc import AsyncIterable
from uuid import UUID

import aiohttp

from src.infra.services.base import SrvBaseClient

from .dtos import DownloadMediaDTO

_S3_CONNECT_TIMEOUT = 60


async def download_stream(url: str, chunk_size: int = 1024 * 64) -> AsyncIterable[bytes]:
    """Потоково скачивает файл из S3 по предподписанному URL."""

    timeout = aiohttp.ClientTimeout(connect=_S3_CONNECT_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session, session.get(url) as response:
        response.raise_for_status()

        async for chunk in response.content.iter_chunked(chunk_size):
            yield chunk


class SrvMediaClient(SrvBaseClient):

    async def create_download_url(self, media_id: UUID) -> DownloadMediaDTO:
        """Создаёт временный URL для скачивания объекта."""

        async with (
            self._get_token_session() as session,
            session.get(f"/api/v1/attachments/{media_id}/presigned-download") as response,
        ):
            response.raise_for_status()
            data = await response.json()

        return DownloadMediaDTO.model_validate(data)
