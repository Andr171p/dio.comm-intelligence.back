from pydantic import BaseModel, Field, HttpUrl, PositiveInt, SecretStr


class Tokens(BaseModel):
    access_token: SecretStr = Field(description="Короткоживущий токен")
    refresh_token: SecretStr = Field(description="Долгоживущий токен (для получения новой пары)")
    expires_at: PositiveInt = Field(description="Время истечения в timestamp")


class DownloadMediaDTO(BaseModel):
    download_url: HttpUrl = Field(description="Временный URL для прямого скачивания из S3")
    expires_in: PositiveInt = Field(description="Время действия в секундах")
