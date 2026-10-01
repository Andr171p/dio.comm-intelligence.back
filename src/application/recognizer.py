from typing import Protocol

from collections.abc import Buffer
from dataclasses import dataclass

from src.domain.communications.vo import TranscriptRepresentation


@dataclass(frozen=True, slots=True)
class RecognitionOptions:
    filename: str
    content_type: str = "application/octet-stream"

    language: str | None = None
    diarize: bool = True
    min_speakers: int | None = None
    max_speakers: int | None = None

    split_at_ms: tuple[int, ...] = ()
    """Точки (мс от начала аудио), через которые сегменты не должны переходить."""


class SpeechRecognizer(Protocol):

    async def recognize(
        self,
        audio: Buffer,
        options: RecognitionOptions | None = None,
    ) -> TranscriptRepresentation: ...
