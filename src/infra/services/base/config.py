from pydantic import Field, HttpUrl, PositiveInt, SecretStr
from pydantic_settings import BaseSettings


class SrvBaseConfig(BaseSettings):
    base_url: HttpUrl = Field(description="Базовый URL сервера без слешей")
    timeout: PositiveInt = Field(default=30, description="Время ожидания результат запроса в секундах")

    client_id: str = Field(description="Пока заходим под логином админа")
    client_secret: SecretStr = Field(description="Пока заходим под паролем админа")

    token_refresh_margin: PositiveInt = Field(
        default=10,
        description="Погрешность при достижении которой получаем новую пару токенов не дожидаясь протухания",
    )
