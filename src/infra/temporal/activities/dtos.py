from typing import Annotated

from dataclasses import dataclass
from uuid import UUID

from typing_extensions import Doc

from src.application.audio_chunking import AudioChunk, AudioChunkRef
from src.application.recognizer import RecognitionOptions


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
class PrepareAudioChunksInput:
    processing_id: UUID
    source: PreparedAudioRef
    chunks: tuple[AudioChunk, ...]


@dataclass(frozen=True, slots=True)
class TranscribeAudioChunkInput:
    communication_id: UUID
    processing_id: UUID
    chunk: AudioChunkRef
    options: RecognitionOptions


@dataclass(frozen=True, slots=True)
class TranscribedAudioChunkRef:
    """Ссылка на результат распознавания одного чанка."""

    index: int
    storage_key: str
    segment_count: int
