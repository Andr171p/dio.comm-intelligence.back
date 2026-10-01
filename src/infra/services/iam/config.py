from pydantic import Field, HttpUrl, PositiveFloat, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SrvIamConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SRV_IAM_")

    base_url: HttpUrl = Field(description="URL адрес сервера без слешей")
    timeout: PositiveFloat = Field(default=30, description="Таймаут в секундах")

    client_id: str | None = Field(default=None, description="Пока заходим под логином админа")
    client_secret: SecretStr | None = Field(default=None, description="Пока заходим под паролем админа")
