from pathlib import Path

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


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


__all__ = ["AudioConfig", "TemporalConfig"]
