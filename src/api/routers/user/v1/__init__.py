from fastapi import APIRouter

from . import communications

router = APIRouter(prefix="/v1")
router.include_router(communications.router)

__all__ = ["router"]
