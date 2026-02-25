from fastapi import status
from httpx import AsyncClient


def get_auth_request_data(client_id: str, client_secret: str) -> dict[str, str]:
    return {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }


async def get_client_token(
    client: AsyncClient,
    client_id: str,
    client_secret: str,
) -> str:
    response = await client.post(
        "/api/auth/token",
        data=get_auth_request_data(client_id, client_secret),
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]


def get_auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def make_authenticated_client(
    client: AsyncClient,
    client_id: str,
    client_secret: str,
) -> AsyncClient:
    token = await get_client_token(client, client_id, client_secret)
    client.headers.update(get_auth_header(token))
    return client
