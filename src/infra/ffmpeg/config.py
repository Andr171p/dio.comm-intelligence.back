from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class FFmpegConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FFMPEG_")

    path: str = Field(default="ffmpeg", description="Путь до установленного ffmpeg")
    threads: PositiveInt = Field(default=1, description="Количество используемых потоков для обработки")


class FFprobeConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FFPROBE_")

    path: str = Field(default="ffprobe", description="Путь до установленного ffprobe")


ffmpeg_config = FFmpegConfig()
ffprobe_config = FFprobeConfig()
