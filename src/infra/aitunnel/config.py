from pydantic import Field, HttpUrl, PositiveFloat, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AiTunnelRecognizerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AITUNNEL_RECOGNIZER_")

    api_key: SecretStr
    base_url: HttpUrl = Field(description="OpenAI-совместимый API base URL")
    model: str = Field(description="STT (speech-to-text) модель поддерживающая диаризацию")
    timeout: PositiveFloat = Field(default=900.0, description="Таймаут запроса")
