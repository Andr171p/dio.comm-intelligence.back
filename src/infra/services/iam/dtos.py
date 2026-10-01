from pydantic import BaseModel, Field, PositiveInt, SecretStr


class Tokens(BaseModel):
    access_token: SecretStr = Field(description="Короткоживущий токен")
    refresh_token: SecretStr = Field(description="Долгоживущий токен (для получения новой пары)")
    expires_at: PositiveInt = Field(description="Время истечения в timestamp")
