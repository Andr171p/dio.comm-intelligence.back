from pathlib import Path

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class FFmpegConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FFMPEG_")

    path: str = Field(default="ffmpeg", description="Путь до установленного ffmpeg")
    threads: PositiveInt = Field(default=1, description="Количество используемых потоков для обработки")


class FFprobeConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FFPROBE_")

    path: str = Field(default="ffprobe", description="Путь до установленного ffprobe")


class VadConfig(BaseSettings):
    """Конфигурация Voice Activity Detection."""

    model_config = SettingsConfigDict(env_prefix="VAD_")

    model_path: Path = Field(description="Путь до ONNX-модели Silero VAD")

    sample_rate: PositiveInt = Field(default=16_000, description="Частота дискретизации")

    threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Порог для определения тишины")
    negative_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Порог окончания речи. По умолчанию threshold - 0.15",
    )

    min_silence_duration_ms: int = Field(
        default=400,
        ge=0,
        description="Минимальная длительность тишины, после которой речь считается завершённой",
    )
    speech_pad_ms: int = Field(default=30, ge=0, description="Отступ вокруг речевого участка")


ffmpeg_config = FFmpegConfig()
ffprobe_config = FFprobeConfig()
