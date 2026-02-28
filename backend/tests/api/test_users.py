import pytest
from fastapi import status
from httpx import AsyncClient

API_ADMIN_USERS_ENDPOINT = "/api/v1/admin/users"
API_ADMIN_USERS_UID_ENDPOINT = "/api/v1/admin/users/{uid}"
API_USERS_ENDPOINT = "/api/v1/users/me"
NONEXISTENT_USER_UID = "xyz"


async def check_endpoints_access(
    client: AsyncClient,
    headers: dict,
    expected_status: status,
) -> None:
    for request_func in [client.post, client.get]:
        response = await request_func(API_ADMIN_USERS_ENDPOINT, headers=headers)
        assert response.status_code == expected_status

    users_uid_url = API_ADMIN_USERS_UID_ENDPOINT.format(uid="test")
    for request_func in [client.get, client.patch, client.delete]:
        response = await request_func(users_uid_url, headers=headers)
        assert response.status_code == expected_status


def check_user_data(
    user_data: dict,
    expected_full_name: str | None = None,
    expected_email: str | None = None,
    expected_is_admin: bool | None = None,
    deleted: bool = False,
) -> None:
    assert isinstance(user_data, dict)
    assert isinstance(user_data.get("uid"), str)
    assert isinstance(user_data.get("full_name"), str)
    assert isinstance(user_data.get("email"), str)
    assert isinstance(user_data.get("created_at"), str)
    assert isinstance(user_data.get("is_admin"), bool)
    assert "deleted_at" in user_data

    if expected_full_name is not None:
        assert user_data["full_name"] == expected_full_name

    if expected_email is not None:
        assert user_data["email"] == expected_email

    if expected_is_admin is not None:
        assert user_data["is_admin"] == expected_is_admin

    deleted_at = user_data.get("deleted_at")

    if deleted:
        assert isinstance(deleted_at, (str))
    else:
        assert deleted_at is None


async def create_new_user(
    client: AsyncClient,
    full_name: str,
    email: str,
    password: str,
    is_admin: bool,
) -> dict:
    response = await client.post(
        API_ADMIN_USERS_ENDPOINT,
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
            "is_admin": is_admin,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


async def get_user(
    client: AsyncClient,
    uid: str,
    expected_status: status = status.HTTP_200_OK,
) -> dict | None:
    response = await client.get(API_ADMIN_USERS_UID_ENDPOINT.format(uid=uid))
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    return response.json()


async def update_user(
    client: AsyncClient,
    uid: str,
    full_name: str | None = None,
    email: str | None = None,
    password: str | None = None,
    is_admin: bool | None = None,
    expected_status: status = status.HTTP_200_OK,
) -> dict:
    update_data = {}

    for key, value in (
        ("full_name", full_name),
        ("email", email),
        ("password", password),
        ("is_admin", is_admin),
    ):
        if value is not None:
            update_data[key] = value

    response = await client.patch(
        url=API_ADMIN_USERS_UID_ENDPOINT.format(uid=uid),
        json=update_data,
    )
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    return response.json()


async def delete_user(
    client: AsyncClient,
    uid: str,
    expected_status: status = status.HTTP_204_NO_CONTENT,
) -> None:
    response = await client.delete(API_ADMIN_USERS_UID_ENDPOINT.format(uid=uid))
    assert response.status_code == expected_status


@pytest.mark.anyio
async def test_no_credentials(client: AsyncClient) -> None:
    await check_endpoints_access(
        client,
        headers={},
        expected_status=status.HTTP_401_UNAUTHORIZED,
    )


@pytest.mark.anyio
async def test_invalid_token(client: AsyncClient) -> None:
    await check_endpoints_access(
        client,
        headers={"Authorization": "Bearer invalid_token"},
        expected_status=status.HTTP_401_UNAUTHORIZED,
    )


@pytest.mark.anyio
async def test_external_user_access(
    external_client: AsyncClient,
) -> None:
    await check_endpoints_access(
        external_client,
        headers={},
        expected_status=status.HTTP_403_FORBIDDEN,
    )


@pytest.mark.anyio
async def test_get_users(admin_client: AsyncClient) -> None:
    response = await admin_client.get(API_ADMIN_USERS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    for user_data in data:
        check_user_data(user_data)


@pytest.mark.anyio
async def test_get_user_by_id(admin_client: AsyncClient) -> None:
    response = await admin_client.get(API_ADMIN_USERS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    test_uids = [user_data["uid"] for user_data in data]
    assert len(test_uids) > 0

    test_uids.append(NONEXISTENT_USER_UID)

    for uid in test_uids:
        expected_status = (
            status.HTTP_404_NOT_FOUND
            if uid == NONEXISTENT_USER_UID
            else status.HTTP_200_OK
        )

        user_data = await get_user(
            client=admin_client,
            uid=uid,
            expected_status=expected_status,
        )

        if expected_status == status.HTTP_200_OK:
            check_user_data(user_data)


# TODO: complete
