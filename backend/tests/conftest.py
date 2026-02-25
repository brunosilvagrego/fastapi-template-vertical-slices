import pytest
from app.api.deps import get_db_session
from app.core.config import settings
from app.core.database import SessionManager, engine
from app.main import app
from httpx import ASGITransport, AsyncClient

from .utils import make_authenticated_client

BASE_URL = "http://test"


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio backend for all async tests."""
    return "asyncio"


async def get_test_db_session():
    """Test-specific database session that creates a fresh connection each
    time."""
    async with SessionManager() as db_session:
        try:
            yield db_session
        finally:
            await db_session.close()


@pytest.fixture(autouse=True)
async def override_get_db_session():
    """Override the database session dependency for tests."""
    app.dependency_overrides[get_db_session] = get_test_db_session
    yield
    app.dependency_overrides.clear()
    # Clean up any remaining connections
    await engine.dispose()


@pytest.fixture
def client_factory():
    async def _make():
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url=BASE_URL,
        )

    return _make


@pytest.fixture()
async def client(client_factory):
    async with await client_factory() as client:
        yield client


@pytest.fixture
async def admin_client(client_factory):
    async with await client_factory() as client:
        authenticated_client = await make_authenticated_client(
            client=client,
            client_id=settings.ADMIN_CLIENT_ID,
            client_secret=settings.ADMIN_CLIENT_SECRET,
        )
        yield authenticated_client


@pytest.fixture
async def external_client(client_factory):
    async with await client_factory() as client:
        authenticated_client = await make_authenticated_client(
            client=client,
            client_id=settings.EXTERNAL_CLIENT_ID,
            client_secret=settings.EXTERNAL_CLIENT_SECRET,
        )
        yield authenticated_client
