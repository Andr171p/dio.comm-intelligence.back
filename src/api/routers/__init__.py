from fastapi import APIRouter

from . import service, user

router = APIRouter(prefix="/api")

router.include_router(service.router)
router.include_router(user.router)

__all__ = ["router"]
