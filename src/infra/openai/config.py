from pydantic import Field, HttpUrl, PositiveFloat, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenaiRecognizerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENAI_RECOGNIZER_")

    base_url: HttpUrl = Field(description="Базовый URL сервера без слешей")
    api_key: SecretStr = Field(description="Секретный API ключ")
    model: str = Field(description="STT модель", examples=["grok-stt-1.0"])
    timeout: PositiveFloat = Field(default=120, description="Таймаут ожидания запроса")
