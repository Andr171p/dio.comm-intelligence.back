from fastapi import FastAPI

from .exception_handler import setup_exception_handlers
from .lifespan import lifespan
from .routers import router

app = FastAPI(title="DIO Communications Intelligence", lifespan=lifespan)
app.include_router(router)

setup_exception_handlers(app)

__all__ = ["app"]
