from fastapi import APIRouter

from . import communications

router = APIRouter(prefix="/api/user/v1")
router.include_router(communications.router)

__all__ = ["router"]
