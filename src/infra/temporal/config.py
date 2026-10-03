from pathlib import Path

from pydantic import Field, NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.application.audio_chunking import AudioChunkingOptions


class TemporalConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TEMPORAL_")

    address: str = Field(default="localhost:7233", description="Адрес Temporal frontend")
    namespace: str = Field(default="default")
    task_queue: str = Field(
        default="communications",
        description="Очередь задач обработки коммуникаций",
    )
    max_concurrent_activities: PositiveInt = Field(
        default=4,
        description="Максимальное число параллельно запускаемых activities",
    )


class AudioConfig(BaseSettings):
    """Настройки для обработки аудио."""

    model_config = SettingsConfigDict(env_prefix="AUDIO_")

    sample_rate: PositiveInt = Field(default=16_000, description="Частота дискретизации")
    temp_dir: Path | None = Field(default=None, description="Временная директория для сохранения аудио")

    # Крупные чанки: меньше стыков для сопоставления спикеров и меньше платных запросов к ASR.
    # 13 минут FLAC 16 кГц моно ~ 14 МБ, что укладывается в лимит 25 МБ OpenAI-совместимого API.
    chunk_target_duration_ms: PositiveInt = Field(default=600_000, description="Целевая длина чанка")
    chunk_min_duration_ms: PositiveInt = Field(default=60_000, description="Минимальная длина чанка")
    chunk_max_duration_ms: PositiveInt = Field(default=780_000, description="Максимальная длина чанка")
    chunk_boundary_search_ms: NonNegativeInt = Field(
        default=60_000, description="Окно поиска паузы вокруг целевой границы",
    )
    chunk_overlap_ms: NonNegativeInt = Field(
        default=10_000, description="Перекрытие соседних чанков (для сопоставления спикеров)",
    )

    @property
    def chunking_options(self) -> AudioChunkingOptions:
        return AudioChunkingOptions(
            target_duration_ms=self.chunk_target_duration_ms,
            min_duration_ms=self.chunk_min_duration_ms,
            max_duration_ms=self.chunk_max_duration_ms,
            boundary_search_ms=self.chunk_boundary_search_ms,
            overlap_ms=self.chunk_overlap_ms,
        )


__all__ = ["AudioConfig", "TemporalConfig"]
