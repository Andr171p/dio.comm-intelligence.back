from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.infra.database import engine
from src.infra.temporal import TemporalConfig, connect, create_temporal_publisher

temporal_config = TemporalConfig()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    temporal_client = await connect(temporal_config)
    app.state.event_publisher = create_temporal_publisher(temporal_client, temporal_config.task_queue)

    yield

    await engine.dispose()


__all__ = ["lifespan"]

