"""Activities: тонкие адаптеры - данные через `/api/service/v1`, логика в application."""

from typing import Any

import asyncio
import shutil
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from uuid import UUID

import anyio
from temporalio import activity

from src.application.communications.dtos import (
    CommunicationResponse,
    TextRepresentationDTO,
    TranscriptRepresentationDTO,
    UpdateCommunicationDTO,
)
from src.application.recognizer import RecognitionOptions
from src.application.transcription import (
    AudioChunk,
    ChunkTranscript,
    merge_transcripts,
    plan_chunks,
    render_text,
)
from src.infra.ffmpeg import ffmpeg
from src.infra.services.iam import SrvIamConfig, SrvIamTokenProvider
from src.infra.services.media import SrvMediaClient, SrvMediaConfig
from src.infra.whisper import WhisperConfig, WhisperRecognizer

from .config import TranscriptionConfig
from .dtos import (
    AudioChunkFile,
    PrepareAudioParams,
    PreparedAudio,
    SaveTranscriptParams,
    TranscribeChunkParams,
)
from .service_api import ServiceApiClient, ServiceApiConfig

_HEARTBEAT_INTERVAL = 10

transcription_config = TranscriptionConfig()

iam_tokens = SrvIamTokenProvider(SrvIamConfig())  # type: ignore
media_client = SrvMediaClient(SrvMediaConfig(), iam_tokens.get_token)  # type: ignore
service_api = ServiceApiClient(ServiceApiConfig(), iam_tokens.get_token)  # type: ignore
recognizer = WhisperRecognizer(WhisperConfig())  # type: ignore


@asynccontextmanager
async def _heartbeat() -> AsyncIterator[None]:
    """Шлёт heartbeat, пока выполняется долгая операция (ffmpeg, распознавание)."""

    async def beat() -> None:
        while True:
            activity.heartbeat()
            await asyncio.sleep(_HEARTBEAT_INTERVAL)

    task = asyncio.create_task(beat())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def _workdir(communication_id: UUID) -> Path:
    return transcription_config.workdir / str(communication_id)


async def _cut(audio: Path, chunk: AudioChunk) -> AudioChunkFile:
    path = audio.with_name(f"chunk-{chunk.index:03}.flac")
    await ffmpeg.cut(audio, path, start_ms=chunk.start_ms, end_ms=chunk.end_ms)
    return AudioChunkFile(chunk=chunk, path=str(path))


@activity.defn
async def get_communication(communication_id: UUID) -> CommunicationResponse:
    return await service_api.get_communication(communication_id)


@activity.defn
async def prepare_audio(params: PrepareAudioParams) -> PreparedAudio:
    """Извлекает и улучшает звук, режет запись на фрагменты по паузам."""

    config = transcription_config
    workdir = _workdir(params.communication_id)
    await anyio.Path(workdir).mkdir(parents=True, exist_ok=True)

    audio = workdir / "audio.flac"
    download = await media_client.create_download_url(params.media_id)

    async with _heartbeat():
        await ffmpeg.extract_audio(download.download_url, audio, audio_filter=config.audio_filter)

        duration_ms = await ffmpeg.probe_duration_ms(audio)
        silences = await ffmpeg.detect_silences(
            audio, noise_db=config.silence_db, min_duration_ms=config.silence_ms,
        )
        chunks = plan_chunks(
            duration_ms,
            silences,
            target_ms=config.chunk_sec * 1000,
            overlap_ms=config.overlap_sec * 1000,
            search_ms=config.search_sec * 1000,
        )

        files: tuple[AudioChunkFile, ...]
        if len(chunks) == 1:
            files = (AudioChunkFile(chunk=chunks[0], path=str(audio)),)
        else:
            files = tuple([await _cut(audio, chunk) for chunk in chunks])

    activity.logger.info("Prepared %d ms of audio in %d chunk(s)", duration_ms, len(files))
    return PreparedAudio(duration_ms=duration_ms, chunks=files)


@activity.defn
async def transcribe_chunk(params: TranscribeChunkParams) -> ChunkTranscript:
    chunk = params.file.chunk
    path = anyio.Path(params.file.path)
    audio = await path.read_bytes()
    options = RecognitionOptions(
        filename=path.name,
        content_type="audio/flac",
        language=params.language,
        # сегменты не пересекают границы собственного интервала - склейка без дублей
        split_at_ms=(chunk.own_from_ms - chunk.start_ms, chunk.own_to_ms - chunk.start_ms),
    )

    async with _heartbeat():
        transcript = await recognizer.recognize(audio, options)

    return ChunkTranscript(chunk=chunk, transcript=transcript)


@activity.defn
async def save_transcript(params: SaveTranscriptParams) -> None:
    """Склеивает фрагменты и сохраняет представления transcript + text."""

    transcript = merge_transcripts(params.transcripts)
    dto = UpdateCommunicationDTO(
        representations=[
            TranscriptRepresentationDTO.model_validate(transcript),
            TextRepresentationDTO.model_validate(render_text(transcript)),
        ],
    )
    await service_api.update_communication(params.communication_id, dto)


@activity.defn
async def cleanup_audio(communication_id: UUID) -> None:
    await asyncio.to_thread(shutil.rmtree, _workdir(communication_id), ignore_errors=True)


ACTIVITIES: Sequence[Callable[..., Any]] = (
    get_communication,
    prepare_audio,
    transcribe_chunk,
    save_transcript,
    cleanup_audio,
)


async def close() -> None:
    await asyncio.gather(iam_tokens.close(), media_client.close(), service_api.close(), recognizer.close())
