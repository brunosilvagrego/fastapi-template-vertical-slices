from fastapi import APIRouter

from app.api.v1.clients import router as clients_router
from app.api.v1.items import router as items_router

router = APIRouter(prefix="/v1")
router.include_router(clients_router)
router.include_router(items_router)
