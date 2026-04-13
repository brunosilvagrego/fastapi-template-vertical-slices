from collections.abc import AsyncGenerator

import pytest
from app.core.config import settings
from app.core.database import engine
from app.core.deps import get_db_session
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from .utils import make_authenticated_client

BASE_URL = "http://test"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def connection() -> AsyncGenerator[AsyncConnection]:
    async with engine.connect() as conn:
        yield conn


@pytest.fixture(scope="function")
async def db_session(
    connection: AsyncConnection,
) -> AsyncGenerator[AsyncSession]:
    async with connection.begin() as transaction:
        async with AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        ) as session:
            yield session

        await transaction.rollback()


@pytest.fixture(autouse=True)
async def override_get_db_session(db_session: AsyncSession):
    app.dependency_overrides[get_db_session] = lambda: db_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client_factory():
    async def _make():
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url=BASE_URL,
        )

    return _make


@pytest.fixture()
async def http_client(client_factory):
    async with await client_factory() as client:
        yield client


@pytest.fixture
async def http_client_admin(client_factory):
    async with await client_factory() as client:
        authenticated_client = await make_authenticated_client(
            client,
            email=settings.ADMIN_USER_EMAIL,
            password=settings.ADMIN_USER_PASSWORD,
        )
        yield authenticated_client


@pytest.fixture
async def http_client_external(client_factory):
    async with await client_factory() as client:
        authenticated_client = await make_authenticated_client(
            client,
            email=settings.EXTERNAL_USER_EMAIL,
            password=settings.EXTERNAL_USER_PASSWORD,
        )
        yield authenticated_client
