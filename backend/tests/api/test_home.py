import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.anyio
async def test_home(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Hello World"}
