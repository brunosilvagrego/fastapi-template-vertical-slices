import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_str = f"Request: {request.method} {request.url}"
        try:
            response = await call_next(request)
            logger.info(f"{request_str} | Response: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"{request_str} | Failed with exception: {e}")
            raise
