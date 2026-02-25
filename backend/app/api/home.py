import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Home"])


@router.get("/")
def root():
    logger.info("Serving root endpoint.")
    return {"message": "Hello World"}
