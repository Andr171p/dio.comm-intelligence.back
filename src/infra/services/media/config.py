from pydantic import Field, HttpUrl, PositiveFloat, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SrvMediaConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SRV_MEDIA_")

    base_url: HttpUrl = Field(description="URL сервера без слешей")
    timeout: PositiveFloat = Field(default=30, description="Таймаут в секундах")

    client_id: str = Field(description="Пока заходим под логином админа")
    client_secret: SecretStr = Field(description="Пока заходим под паролем админа")
