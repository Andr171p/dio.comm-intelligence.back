from typing import Annotated, Literal

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from typing_extensions import Doc

from src.domain.communications.types import RepresentationType


@dataclass(frozen=True, slots=True, kw_only=True)
class TranscriptSegment:
    """Распознанная часть аудио."""

    id: str
    speaker: str
    text: str
    started_ms: Annotated[int | None, Doc("Начало фрагмента в миллисекундах от начала записи")] = None
    ended_ms: Annotated[int | None, Doc("Конец фрагмента в миллисекундах от начала записи")] = None
    confidence: Annotated[float | None, Doc("Уверенность модели распознавания речи")] = None


@dataclass(frozen=True, slots=True)
class TranscriptRepresentation:
    """Транскрибация исходной коммуникации."""

    segments: tuple[TranscriptSegment, ...]
    language: str | None = None

    type: Literal[RepresentationType.TRANSCRIPT] = RepresentationType.TRANSCRIPT


@dataclass(frozen=True, slots=True)
class Message:
    """Сообщение из произвольного чата."""

    id: str
    created_at: datetime

    text: str | None = None
    attachments: tuple[UUID, ...] = ()

    reply_to_id: str | None = None
    thread_id: str | None = None


@dataclass(frozen=True, slots=True)
class ChatRepresentation:
    """Нормализованное представление чата."""

    messages: tuple[Message, ...]
    type: Literal[RepresentationType.CHAT] = RepresentationType.CHAT


@dataclass(frozen=True, slots=True)
class TextRepresentation:
    """Представление коммуникации в виде непрерывного текста."""

    content: str
    language: str | None = None

    type: Literal[RepresentationType.TEXT] = RepresentationType.TEXT


type CommunicationRepresentation = ChatRepresentation | TranscriptRepresentation | TextRepresentation


__all__ = [
    "ChatRepresentation",
    "CommunicationRepresentation",
    "Message",
    "TextRepresentation",
    "TranscriptRepresentation",
    "TranscriptSegment",
]
