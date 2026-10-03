from pydantic_settings import SettingsConfigDict

from src.infra.services.base import SrvBaseConfig


class SrvCommunicationsConfig(SrvBaseConfig):
    model_config = SettingsConfigDict(env_prefix="SRV_COMMUNICATIONS_")
