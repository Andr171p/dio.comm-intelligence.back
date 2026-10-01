"""HTTP API: `uvicorn src.api.app:app`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from ddf.application.exceptions import ApplicationError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.dependencies.auth import iam_client
from src.api.routers import router
from src.infra.database import engine
from src.infra.temporal import TemporalConfig, connect, create_temporal_publisher

temporal_config = TemporalConfig()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    temporal_client = await connect(temporal_config)
    app.state.event_publisher = create_temporal_publisher(temporal_client, temporal_config.task_queue)

    yield

    await iam_client.close()
    await engine.dispose()


async def handle_application_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApplicationError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message, "details": exc.details},
    )


app = FastAPI(title="DIO Communication Intelligence", lifespan=lifespan)
app.include_router(router)
app.add_exception_handler(ApplicationError, handle_application_error)
