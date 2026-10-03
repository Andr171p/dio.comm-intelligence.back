from pydantic import Field, HttpUrl, PositiveFloat
from pydantic_settings import BaseSettings, SettingsConfigDict


class SrvIamConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SRV_IAM_")

    base_url: HttpUrl = Field(description="URL адрес сервера без слешей")
    timeout: PositiveFloat = Field(default=30, description="Таймаут в секундах")
