from pydantic import BaseModel, Field, PositiveInt


class DownloadMediaDTO(BaseModel):
    download_url: str = Field(description="Временный URL для прямого скачивания из S3")
    expires_in: PositiveInt = Field(description="Время действия в секундах")
