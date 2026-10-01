from pydantic import Field, HttpUrl, PositiveFloat
from pydantic_settings import BaseSettings, SettingsConfigDict


class SrvMediaConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SRV_MEDIA_")

    base_url: HttpUrl = Field(description="URL сервера без слешей")
    timeout: PositiveFloat = Field(default=30, description="Таймаут в секундах")
