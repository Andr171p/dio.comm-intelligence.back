from fastapi import APIRouter

from src.api.dependencies.auth import require_auth_service

from . import communications

router = APIRouter(prefix="/v1", dependencies=[require_auth_service])

router.include_router(communications.router)

__all__ = ["router"]
