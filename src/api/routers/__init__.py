from fastapi import APIRouter

from .service.v1 import router as service_router
from .user.v1 import router as user_router

router = APIRouter()
router.include_router(user_router)
router.include_router(service_router)

__all__ = ["router"]
