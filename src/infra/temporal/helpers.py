import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from tempfile import TemporaryDirectory
from uuid import UUID

import aiofiles
from anyio import Path
from temporalio import activity

from src.application.audio_chunking import AudioChunk
from src.infra.ffmpeg.chunking import extract_audio_chunk
from src.infra.s3 import S3Client
from src.infra.services.media import SrvMediaClient, download_stream

from .config import AudioConfig


def build_audio_chunk_key(chunk: AudioChunk) -> str:
    return f"{chunk.index:04d}-{chunk.start_ms}-{chunk.end_ms}"


@asynccontextmanager
async def materialize_audio_chunk(
    source: Path,
    chunk: AudioChunk,
    config: AudioConfig,
) -> AsyncIterator[Path]:
    """Временно сохраняет аудио чанк на диск."""

    with TemporaryDirectory(dir=config.temp_dir, prefix="audio-chunk") as temp_dir:
        path = Path(temp_dir) / f"{build_audio_chunk_key(chunk)}.flac"
        await extract_audio_chunk(source, path, chunk)
        yield path


@asynccontextmanager
async def heartbeat_periodically(*, interval: float = 10.0, detail: str | None = None) -> AsyncIterator[None]:
    """Периодический temporal activity heartbeat для долгих операций."""

    async def run() -> None:
        while True:
            activity.heartbeat(detail)
            await asyncio.sleep(interval)

    task = asyncio.create_task(run())

    try:
        yield
    finally:
        task.cancel()

        with suppress(asyncio.CancelledError):
            await task


async def download_to_from_s3(s3_client: S3Client, storage_key: str, path: Path) -> None:
    """Скачивает объект из S3 и сохраняет на диск."""

    async with aiofiles.open(str(path), mode="wb") as file:
        async for chunk in s3_client.download_stream(storage_key):
            await file.write(chunk)


async def download_to_from_media(media_client: SrvMediaClient, media_id: UUID, path: Path) -> None:
    """Скачивает файл на диск из Media Service."""

    dto = await media_client.create_download_url(media_id)

    async with aiofiles.open(str(path), mode="wb") as file:
        async for chunk in download_stream(str(dto.download_url)):
            await file.write(chunk)
