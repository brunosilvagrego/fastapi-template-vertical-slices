from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

API_HEALTH_ENDPOINT = "/api/health"


@pytest.mark.anyio
async def test_health_status(client: AsyncClient) -> None:
    """Test running database."""
    response = await client.get(API_HEALTH_ENDPOINT)
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.anyio
@pytest.mark.parametrize(
    "db_health,expected_status",
    [
        (False, status.HTTP_503_SERVICE_UNAVAILABLE),
        (True, status.HTTP_204_NO_CONTENT),
    ],
)
@patch("app.api.health.db_health_check", new_callable=AsyncMock)
async def test_health_status_mocked(
    mock_db_health_check: AsyncMock,
    client: AsyncClient,
    db_health: bool,
    expected_status: int,
) -> None:
    """Test health status with mocked database health check."""
    mock_db_health_check.return_value = db_health
    response = await client.get(API_HEALTH_ENDPOINT)
    assert response.status_code == expected_status
