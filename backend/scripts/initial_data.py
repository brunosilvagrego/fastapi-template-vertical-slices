import asyncio
import logging
import os

from app.core.config import settings
from app.core.consts import Environment
from app.core.database import SessionManager
from app.core.logging_config import setup_logging
from app.core.security import get_password_hash
from app.services import clients as service_clients

setup_logging()
logger = logging.getLogger(__name__)


async def create_users():
    env = os.getenv("ENVIRONMENT", Environment.PRODUCTION)
    logger.info(f"Running initial data script for environment: {env}")

    async with SessionManager() as db_session:
        clients = await service_clients.get_all(db_session)

        if clients:
            logger.info(
                "Clients already exist. Skipping initial clients creation."
            )
            return

        await service_clients.create(
            db_session=db_session,
            name=settings.ADMIN_CLIENT_NAME,
            oauth_id=settings.ADMIN_CLIENT_ID,
            oauth_secret_hash=get_password_hash(settings.ADMIN_CLIENT_SECRET),
            is_admin=True,
        )
        logger.info("Admin client created.")

        if env in (Environment.DEVELOPMENT, Environment.TESTING):
            await service_clients.create(
                db_session=db_session,
                name=settings.EXTERNAL_CLIENT_NAME,
                oauth_id=settings.EXTERNAL_CLIENT_ID,
                oauth_secret_hash=get_password_hash(
                    settings.EXTERNAL_CLIENT_SECRET
                ),
                is_admin=False,
            )
            logger.info("External client created.")


if __name__ == "__main__":
    asyncio.run(create_users())
