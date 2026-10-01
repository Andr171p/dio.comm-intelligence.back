from pydantic import Field, HttpUrl, PositiveFloat
from pydantic_settings import BaseSettings, SettingsConfigDict


class WhisperConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WHISPER_")

    base_url: HttpUrl = Field(description="Базовый URL ASR Whisper ASR сервиса")
    timeout: PositiveFloat = Field(default=600, description="Таймаут распознавания в секундах")
