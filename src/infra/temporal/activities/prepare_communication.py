import asyncio
from tempfile import TemporaryDirectory

import aiofiles
from anyio import Path
from temporalio import activity
from temporalio.exceptions import ApplicationError

from src.application.audio_chunking import AudioChunkingOptions, plan_audio_chunks
from src.infra.ffmpeg.utils import prepare_audio
from src.infra.temporal.helpers import download_to_from_media, heartbeat_periodically

from .definitions import audio_config, communications_client, media_client, s3_client
from .dtos import AudioPreparationResult, CommunicationProcessingInput, PreparedAudioRef

# TODO: Вынести в config
options = AudioChunkingOptions(
    target_duration_ms=60_000,
    max_duration_ms=90_000,
    min_duration_ms=10_000,
    boundary_search_ms=10_000,
    overlap_ms=1_000,
)


@activity.defn(name="prepare_communication")
async def prepare_communication(input: CommunicationProcessingInput) -> ...:
    """Подготавливает исходное медиа к дальнейшей обработке.

    Activity:

        1. Загружает Communication и определяет исходное медиа.
        2. Скачивает media во временный локальный файл.
        3. Извлекает и нормализует аудиодорожку в FLAC.
        4. Потоково выполняет VAD.
        5. Строит логический план чанков.
        6. Загружает подготовленное аудио в processing storage.

    В Temporal возвращаются только компактные ссылки и временные
    диапазоны. Содержимое аудио через Workflow History не передаётся.

    Операция идемпотентна относительно Temporal retry, поскольку
    storage key детерминирован через ``processing_id``.
    """

    communication = await communications_client.get_communication(input.communication_id)

    if communication is None:
        raise ApplicationError(
            f"Communication with ID {input.communication_id!r} not found.",
            non_retryable=True,
        )

    if communication.original_media_id is None:
        raise ApplicationError(
            f"Communication with ID {communication.id!r} has no original media.",
            non_retryable=True,
        )

    storage_key = f"processing/{input.processing_id}/prepared/audio.flac"

    with TemporaryDirectory(dir=audio_config.temp_dir, prefix="prepare-audio-") as temp_dir:
        temp_path = Path(temp_dir)

        original_path = temp_path / "original"
        prepared_path = temp_path / "prepared.flac"

        # 1. Download original media
        async with heartbeat_periodically(detail="downloading-media"):
            await download_to_from_media(media_client, communication.original_media_id, original_path)

        # 2. Extract + normalize audio
        async with heartbeat_periodically(detail="preparing-audio"):
            meta = await prepare_audio(original_path, prepared_path)

        # 3. Voice Activity Detection (VAD)
        async with heartbeat_periodically(detail="detecting-voice-activity"):
            from src.infra.vad.silero import get_silero_vad

            vad = get_silero_vad()
            boundaries = await asyncio.to_thread(vad.detect_boundaries, prepared_path)

        # 4. Chunk planning
        chunks = plan_audio_chunks(
            duration_ms=meta.duration_ms,
            boundaries=boundaries,
            options=...,
        )

        # 5. Durable prepared audio
        async with (
            heartbeat_periodically(detail="uploading-prepared-audio"),
            aiofiles.open(prepared_path, mode="rb") as file,
        ):
            await s3_client.upload_stream(file, storage_key, "audio/flac")

    ref = PreparedAudioRef(
        storage_key=storage_key,
        duration_ms=meta.duration_ms,
        sample_rate=meta.sample_rate,
        channels=meta.channels,
    )
    return AudioPreparationResult(audio=ref, chunks=chunks)
