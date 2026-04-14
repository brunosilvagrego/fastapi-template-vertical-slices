import logging

from fastapi import APIRouter, status
from starlette.responses import Response

from app.core.database import db_health_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Service health check",
    description=(
        "Verifies that the API and its backing database are reachable.\n\n"
        "Returns **204 No Content** when all dependencies are healthy, or "
        "**503 Service Unavailable** when the database health check fails. "
        "This endpoint is intentionally unauthenticated so that load "
        "balancers and orchestration platforms (e.g. Kubernetes liveness "
        "probes) can poll it without credentials."
    ),
    response_description="No content — the service is healthy.",
    responses={
        503: {
            "description": "The database is unreachable or returned an "
            "unexpected result.",
        },
    },
)
async def health() -> Response:
    """Return the API health status.

    Executes a lightweight database ping via
    :func:`~app.core.database.db_health_check`.

    Any exception raised during the check is caught, logged, and converted
    into a ``503`` response so that the endpoint never propagates uncaught
    errors to the caller.

    Returns:
        A :class:`starlette.responses.Response` with status ``204`` when the
        database is healthy, or ``503`` otherwise.
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        if await db_health_check() is True:
            status_code = status.HTTP_204_NO_CONTENT
    except Exception as e:  # noqa: BLE001
        logger.error(f"Database health check failed: {e}")

    return Response(status_code=status_code)
