import random
import string
from datetime import datetime, timedelta

import jwt
from app.core.config import settings
from app.core.consts import API_AUTH_ENDPOINT, PASSWORD_MIN_LENGTH
from app.core.security import decode_access_token
from app.core.utils import now_utc
from fastapi import status
from httpx import AsyncClient

PASSWORD_CHARACTERS = string.ascii_letters + string.digits


def get_auth_request_data(email: str, password: str) -> dict[str, str]:
    return {
        "grant_type": "password",
        "username": email,
        "password": password,
    }


async def get_user_token(
    client: AsyncClient,
    email: str,
    password: str,
    expected_status: status = status.HTTP_200_OK,
) -> str | None:
    response = await client.post(
        API_AUTH_ENDPOINT,
        data=get_auth_request_data(email, password),
    )
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    return response.json()["access_token"]


def get_auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def make_authenticated_client(
    client: AsyncClient,
    email: str,
    password: str,
) -> AsyncClient:
    token = await get_user_token(client, email, password)
    assert token is not None
    client.headers.update(get_auth_header(token))
    return client


def get_auth_header_invalid_token() -> dict[str, str]:
    return get_auth_header("invalid_token")


def create_access_token(user_uid: str, expire: datetime) -> str:
    return jwt.encode(
        payload={"sub": user_uid, "exp": expire},
        key=settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def get_auth_header_expired_token() -> dict[str, str]:
    expire = now_utc() - timedelta(minutes=5)
    expired_token = create_access_token(user_uid="test", expire=expire)

    return get_auth_header(expired_token)


def random_password(
    length: int = PASSWORD_MIN_LENGTH,
    alphabet: str = PASSWORD_CHARACTERS,
):
    return "".join(random.choice(alphabet) for _ in range(length))  # noqa: S311


async def validate_user_password(
    client: AsyncClient,
    uid: str,
    email: str,
    password: str,
    expected_status: status = status.HTTP_200_OK,
) -> None:
    token = await get_user_token(client, email, password, expected_status)

    if expected_status != status.HTTP_200_OK:
        return

    token_data = decode_access_token(token)
    assert token_data.uid == uid


def is_iso_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False
