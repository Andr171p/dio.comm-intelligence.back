"""Внешний контракт Whisper ACR."""

from collections.abc import Sequence

from pydantic import BaseModel, Field, NonNegativeFloat


class WhisperWord(BaseModel):
    word: str = Field(description="Распознанное слово или токен")

    start: NonNegativeFloat | None = Field(
        default=None,
        description="Время начала воспроизведения слова в секундах от начала аудио",
    )
    end: NonNegativeFloat | None = Field(
        default=None,
        description="Время окончания воспроизведения слова в секундах от начала аудио",
    )

    score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Уверенность модели в распознавании слова (от 0.0 до 1.0)",
    )
    speaker: str | None = Field(default=None, description="Идентификатор спикера для данного слова")


class WhisperSegment(BaseModel):
    id: int | str | None = Field(
        default=None, description="Уникальный идентификатор сегмента (индекс или UUID)",
    )

    start: NonNegativeFloat | None = Field(default=None, description="Время начала сегмента в секундах")
    end: NonNegativeFloat | None = Field(default=None, description="Время окончания сегмента в секундах")

    text: str = Field(description="Распознанный аудио сегмент")
    speaker: str | None = Field(default=None, description="Идентификатор/метка спикера")

    words: Sequence[WhisperWord] = Field(
        default_factory=list, description="Список отдельных слов внутри сегмента",
    )


class WhisperResponse(BaseModel):
    language: str | None = Field(
        default=None,
        description="Код определенного или заданного языка",
        examples=["ru", "en"],
    )
    text: str | None = Field(default=None, description="Полностью распознанный текст")

    segments: Sequence[WhisperSegment] = Field(
        default_factory=list,
        description="Последовательность распознанных речевых сегментов",
    )
