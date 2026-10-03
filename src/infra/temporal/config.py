from pathlib import Path

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class TemporalConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TEMPORAL_")

    address: str = Field(default="localhost:7233", description="Адрес Temporal frontend")
    namespace: str = Field(default="default")
    task_queue: str = Field(default="communications", description="Очередь задач обработки коммуникаций")
    max_concurrent_activities: PositiveInt = Field(default=4, description="Параллельные activities воркера")


class TranscriptionConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRANSCRIPTION_")

    workdir: Path = Field(
        default=Path(".data/transcription"),
        description="Рабочая директория аудио (общая для всех реплик воркера)",
    )
    audio_filter: str = Field(
        default="highpass=f=80,afftdn,dynaudnorm",
        description="ffmpeg-фильтр улучшения речи: срез гула, шумоподавление, выравнивание громкости",
    )

    chunk_sec: PositiveInt = Field(default=600, description="Целевая длина фрагмента")
    search_sec: PositiveInt = Field(default=60, description="Окно поиска паузы вокруг точки разреза")
    overlap_sec: PositiveInt = Field(default=5, description="Перекрытие соседних фрагментов")

    silence_db: float = Field(default=-30, description="Порог тишины, dB")
    silence_ms: PositiveInt = Field(default=400, description="Минимальная длина паузы")


class AudioConfig(BaseSettings):
    """Настройки для обработки аудио."""

    model_config = SettingsConfigDict(env_prefix="AUDIO_")

    sample_rate: PositiveInt = Field(default=16_000, description="Частота дискретизации")
    temp_dir: Path | None = Field(default=None, description="Временная директория для сохранения аудио")


__all__ = ["AudioConfig", "TemporalConfig", "TranscriptionConfig"]
