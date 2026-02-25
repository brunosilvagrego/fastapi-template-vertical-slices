import jwt
import pytest
from app.core.config import settings
from fastapi import status
from httpx import AsyncClient

from tests.utils import get_auth_request_data

API_AUTH_ENDPOINT = "/api/auth/token"


@pytest.mark.anyio
async def test_no_credentials(client: AsyncClient) -> None:
    response = await client.post(API_AUTH_ENDPOINT)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_invalid_credentials(client: AsyncClient) -> None:
    response = await client.post(
        API_AUTH_ENDPOINT,
        data=get_auth_request_data("invalid", "invalid"),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
@pytest.mark.parametrize(
    "client_id,client_secret",
    [
        (settings.ADMIN_CLIENT_ID, settings.ADMIN_CLIENT_SECRET),
        (settings.EXTERNAL_CLIENT_ID, settings.EXTERNAL_CLIENT_SECRET),
    ],
)
async def test_valid_credentials(
    client: AsyncClient,
    client_id: str,
    client_secret: str,
) -> None:
    response = await client.post(
        API_AUTH_ENDPOINT,
        data=get_auth_request_data(client_id, client_secret),
    )
    assert response.status_code == status.HTTP_200_OK

    token_data: dict = response.json()

    token_type = token_data.get("token_type")
    assert token_type == settings.JWT_TOKEN_TYPE

    access_token = token_data.get("access_token")
    assert access_token is not None

    payload = jwt.decode(
        jwt=access_token,
        key=settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert payload.get("sub") == client_id
    assert isinstance(payload.get("exp"), int)
