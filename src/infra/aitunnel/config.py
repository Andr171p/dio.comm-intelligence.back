from pydantic import Field, HttpUrl, PositiveFloat, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AiTunnelRecognizerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AITUNNEL_RECOGNIZER_")

    api_key: SecretStr
    base_url: HttpUrl = Field(description="OpenAI-совместимый API base URL")
    model: str = Field(description="STT (speech-to-text) модель")
    diarization: bool = Field(
        default=True,
        description="Модель поддерживает diarized_json (иначе verbose_json без разметки спикеров)",
    )
    language: str | None = Field(
        default="ru",
        description="Язык по умолчанию (ISO-639-1), без него модель может переводить речь на английский",
    )
    timeout: PositiveFloat = Field(default=900.0, description="Таймаут запроса")
