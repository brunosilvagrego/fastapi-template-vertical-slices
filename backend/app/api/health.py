import logging

from fastapi import APIRouter, status
from starlette.responses import Response

from app.core.database import db_health_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=status.HTTP_204_NO_CONTENT)
async def health():
    """Return the API health status."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        if await db_health_check() is True:
            status_code = status.HTTP_204_NO_CONTENT
    except Exception as e:  # noqa: BLE001
        logger.error(f"Database health check failed: {e}")

    return Response(status_code=status_code)
