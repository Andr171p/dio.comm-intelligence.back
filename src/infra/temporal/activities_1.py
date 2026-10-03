from typing import Annotated

from dataclasses import dataclass
from tempfile import TemporaryDirectory
from uuid import UUID

import aiofiles
from temporalio import activity
from typing_extensions import Doc

from src.application.audio_chunking import AudioChunk, AudioChunkRef
from src.infra.s3 import S3Client, S3Config

from .config import AudioConfig
from .helpers import build_audio_chunk_key, download_to_from_s3, materialize_audio_chunk

audio_config = AudioConfig()

s3_config = S3Config()  # type: ignore
s3_client = S3Client(s3_config)


@dataclass(frozen=True, slots=True)
class CommunicationProcessingInput:
    communication_id: UUID
    processing_id: Annotated[UUID, Doc("Детерминированный идентификатор всего пайплайна обработки")]


@dataclass(frozen=True, slots=True)
class PreparedAudioRef:
    """Ссылка на подготовленный аудио файл."""

    storage_key: str

    duration_ms: int
    sample_rate: int
    channels: int


@dataclass(frozen=True, slots=True)
class AudioPreparationResult:
    """Результат подготовки аудио."""

    audio: PreparedAudioRef
    chunks: tuple[AudioChunk, ...]


@dataclass(frozen=True, slots=True)
class PrepareAudioChunksInput:
    processing_id: UUID
    source: PreparedAudioRef
    chunks: tuple[AudioChunk, ...]


@dataclass(frozen=True, slots=True)
class TranscribeAudioChunkInput:
    communication_id: UUID
    processing_id: UUID
    chunk: AudioChunkRef


@activity.defn(name="prepare_audio_chunks")
async def prepare_audio_chunks(input: PrepareAudioChunksInput) -> tuple[AudioChunkRef, ...]:
    refs: list[AudioChunkRef] = []

    with TemporaryDirectory(audio_config.temp_dir) as temp_dir:
        source = f"{temp_dir}/prepared.flac"
        await download_to_from_s3(s3_client, input.source.storage_key, source)

        for chunk in input.chunks:
            key = build_audio_chunk_key(chunk)
            storage_key = f"processing/{input.processing_id}/chunks/{key}.flac"

            async with (
                materialize_audio_chunk(source, chunk, audio_config) as path,
                aiofiles.open(str(path), mode="rb") as file,
            ):
                await s3_client.upload_stream(file, storage_key, "audio/flac")

            activity.heartbeat()

            refs.append(
                AudioChunkRef(
                    index=chunk.index,
                    storage_key=storage_key,
                    start_ms=chunk.start_ms,
                    end_ms=chunk.end_ms,
                    accepted_start_ms=chunk.accepted_start_ms,
                    accepted_end_ms=chunk.accepted_end_ms,
                )
            )

    return tuple(refs)
