import asyncio
import logging
import os

from app.core.config import settings
from app.core.consts import Environment
from app.core.database import SessionManager
from app.core.logging_config import setup_logging
from app.core.security import get_password_hash
from app.users import service as service_users

setup_logging()
logger = logging.getLogger(__name__)


async def create_users():
    env = os.getenv("ENVIRONMENT", Environment.PRODUCTION)
    logger.info(f"Running initial data script for environment: {env}")

    async with SessionManager() as db_session:
        users = await service_users.get_all(db_session)

        if users:
            logger.info("Users already exist. Skipping initial users creation.")
            return

        await service_users.create(
            db_session=db_session,
            full_name=settings.ADMIN_USER_FULL_NAME,
            email=settings.ADMIN_USER_EMAIL,
            hashed_password=get_password_hash(settings.ADMIN_USER_PASSWORD),
            is_admin=True,
        )
        logger.info("Admin user created.")

        if env in (Environment.DEVELOPMENT, Environment.TESTING):
            await service_users.create(
                db_session=db_session,
                full_name=settings.EXTERNAL_USER_FULL_NAME,
                email=settings.EXTERNAL_USER_EMAIL,
                hashed_password=get_password_hash(
                    settings.EXTERNAL_USER_PASSWORD
                ),
                is_admin=False,
            )
            logger.info("External user created.")


if __name__ == "__main__":
    asyncio.run(create_users())
