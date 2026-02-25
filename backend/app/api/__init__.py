from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.v1 import router as api_v1_router

router = APIRouter(prefix="/api")
router.include_router(auth_router)
router.include_router(health_router)
router.include_router(api_v1_router)
