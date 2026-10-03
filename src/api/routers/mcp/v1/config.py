from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class McpConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCP_")

    resource_url: str = Field(
        default="http://localhost:8000/api/mcp/v1",
        description="Публичный URL MCP сервера (resource identifier для OAuth metadata)",
    )
    issuer_url: str = Field(
        default="http://localhost:8001",
        description="IAM DIOS, который выдаёт access токены",
    )
    allowed_hosts: list[str] = Field(
        default=["localhost:*", "127.0.0.1:*"],
        description="Допустимые Host заголовки (защита от DNS rebinding)",
    )
    default_timezone: str = Field(
        default="UTC",
        description="Часовой пояс для дат без смещения, которые передал агент",
    )


mcp_config = McpConfig()
