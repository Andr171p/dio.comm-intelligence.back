from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from .config import TemporalConfig


async def connect(config: TemporalConfig) -> Client:
    return await Client.connect(
        config.address, namespace=config.namespace, data_converter=pydantic_data_converter,
    )
