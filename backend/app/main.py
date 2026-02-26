import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.auth.router import router as router_auth
from app.clients.router import router as router_clients
from app.core.logging_config import setup_logging
from app.health.router import router as router_health
from app.items.router import router as router_items

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Context manager that handles startup and shutdown of the app."""
    logger.info("Starting up the application.")
    # TODO: initialize resources

    yield

    logger.info("Shutting down the application.")
    # TODO: clean up resources


app = FastAPI(title="<Service Name> API", lifespan=lifespan)

router = APIRouter()


@router.get("/")
def root():
    logger.info("Serving root endpoint.")
    return {"message": "Hello World"}


# Root routers
router.include_router(router_health)

# API routers
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(router_auth)
api_router.include_router(router_clients)
api_router.include_router(router_items)

# App routers
app.include_router(router)
app.include_router(api_router)
