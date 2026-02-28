import jwt
import pytest
from app.core.config import settings
from app.core.consts import API_AUTH_ENDPOINT
from fastapi import status
from httpx import AsyncClient

from tests.utils import get_auth_request_data


@pytest.mark.anyio
async def test_no_credentials(client: AsyncClient) -> None:
    response = await client.post(API_AUTH_ENDPOINT)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.anyio
async def test_invalid_credentials(client: AsyncClient) -> None:
    response = await client.post(
        API_AUTH_ENDPOINT,
        data=get_auth_request_data("invalid", "invalid"),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
@pytest.mark.parametrize(
    "email,password",
    [
        (settings.ADMIN_USER_EMAIL, settings.ADMIN_USER_PASSWORD),
        (settings.EXTERNAL_USER_EMAIL, settings.EXTERNAL_USER_PASSWORD),
    ],
)
async def test_valid_credentials(
    client: AsyncClient,
    email: str,
    password: str,
) -> None:
    response = await client.post(
        API_AUTH_ENDPOINT,
        data=get_auth_request_data(email, password),
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
    assert isinstance(payload.get("sub"), str)
    assert isinstance(payload.get("exp"), int)
