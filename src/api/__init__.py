from fastapi import FastAPI

from .exception_handler import setup_exception_handlers
from .lifespan import lifespan
from .routers import router
from .routers.mcp import mcp_app

app = FastAPI(title="DIO Communications Intelligence", lifespan=lifespan)
app.include_router(router)
app.mount("/api/mcp", mcp_app)  # MCP endpoint: /api/mcp/v1

setup_exception_handlers(app)

__all__ = ["app"]
