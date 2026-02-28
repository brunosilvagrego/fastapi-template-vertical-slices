from app.core.consts import API_AUTH_ENDPOINT
from fastapi import status
from httpx import AsyncClient


def get_auth_request_data(email: str, password: str) -> dict[str, str]:
    return {
        "grant_type": "password",
        "username": email,
        "password": password,
    }


async def get_user_token(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        API_AUTH_ENDPOINT,
        data=get_auth_request_data(email, password),
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]


def get_auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def make_authenticated_client(
    client: AsyncClient,
    email: str,
    password: str,
) -> AsyncClient:
    token = await get_user_token(client, email, password)
    client.headers.update(get_auth_header(token))
    return client
