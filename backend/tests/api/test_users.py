import pytest
from app.core.config import settings
from app.core.consts import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from fastapi import status
from httpx import AsyncClient

from tests.utils import (
    is_iso_datetime,
    make_authenticated_client,
    random_password,
    validate_user_password,
)

API_ADMIN_USERS_ENDPOINT = "/api/v1/admin/users"
API_ADMIN_USERS_UID_ENDPOINT = "/api/v1/admin/users/{uid}"
API_USERS_ENDPOINT = "/api/v1/users/me"
SELF_UID = "me"
NONEXISTENT_USER_UID = "xyz"
INVALID_EMAIL = "invalid_email"


async def check_admin_endpoints_access(
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


async def check_user_endpoints_access(
    client: AsyncClient,
    headers: dict,
    expected_status: status,
) -> None:
    for request_func in [client.get, client.patch]:
        response = await request_func(API_USERS_ENDPOINT, headers=headers)
        assert response.status_code == expected_status


def check_user_data(
    user_data: dict,
    expected_full_name: str | None = None,
    expected_email: str | None = None,
    expected_is_admin: bool | None = None,
    self_data: bool = False,
) -> None:
    assert isinstance(user_data, dict)
    assert isinstance(user_data.get("full_name"), str)
    assert isinstance(user_data.get("email"), str)

    if self_data is True:
        joined_ts = user_data.get("joined_at")
    else:
        assert isinstance(user_data.get("uid"), str)
        assert isinstance(user_data.get("is_admin"), bool)
        assert "deleted_at" in user_data
        assert user_data.get("deleted_at") is None
        joined_ts = user_data.get("created_at")

    assert isinstance(joined_ts, str)
    assert is_iso_datetime(joined_ts)

    if expected_full_name is not None:
        assert user_data["full_name"] == expected_full_name

    if expected_email is not None:
        assert user_data["email"] == expected_email

    if expected_is_admin is not None:
        assert user_data["is_admin"] == expected_is_admin


async def create_new_user(
    client: AsyncClient,
    full_name: str,
    email: str | None = None,
    password: str | None = None,
    is_admin: bool = False,
    expected_status: status = status.HTTP_201_CREATED,
) -> dict | None:
    if email is None:
        email = f"{full_name.lower().replace(' ', '')}@example.com"

    if password is None:
        password = random_password()

    response = await client.post(
        API_ADMIN_USERS_ENDPOINT,
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
            "is_admin": is_admin,
        },
    )
    assert response.status_code == expected_status

    if expected_status != status.HTTP_201_CREATED:
        return None

    return response.json()


async def get_all_users(
    client: AsyncClient,
    expected_status: status = status.HTTP_200_OK,
) -> dict | None:
    response = await client.get(API_ADMIN_USERS_ENDPOINT)
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    data = response.json()
    assert isinstance(data, list)

    return data


def get_user_url(uid: str):
    return (
        API_USERS_ENDPOINT
        if uid == SELF_UID
        else API_ADMIN_USERS_UID_ENDPOINT.format(uid=uid)
    )


async def get_user(
    client: AsyncClient,
    uid: str,
    expected_status: status = status.HTTP_200_OK,
) -> dict | None:
    url = get_user_url(uid)
    response = await client.get(url)
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

    url = get_user_url(uid)
    response = await client.patch(url, json=update_data)
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
    for check_access_function in (
        check_admin_endpoints_access,
        check_user_endpoints_access,
    ):
        await check_access_function(
            client,
            headers={},
            expected_status=status.HTTP_401_UNAUTHORIZED,
        )


@pytest.mark.anyio
async def test_invalid_token(client: AsyncClient) -> None:
    for check_access_function in (
        check_admin_endpoints_access,
        check_user_endpoints_access,
    ):
        await check_access_function(
            client,
            headers={"Authorization": "Bearer invalid_token"},
            expected_status=status.HTTP_401_UNAUTHORIZED,
        )


# TODO: test expired token


@pytest.mark.anyio
async def test_external_user_access(
    external_client: AsyncClient,
) -> None:
    await check_admin_endpoints_access(
        external_client,
        headers={},
        expected_status=status.HTTP_403_FORBIDDEN,
    )


@pytest.mark.anyio
async def test_admin_get_users(admin_client: AsyncClient) -> None:
    data = await get_all_users(admin_client)
    assert len(data) > 0

    for user_data in data:
        check_user_data(user_data)


@pytest.mark.anyio
async def test_admin_get_user_by_id(admin_client: AsyncClient) -> None:
    data = await get_all_users(admin_client)

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


@pytest.mark.anyio
async def test_admin_create_users(admin_client: AsyncClient) -> None:
    for i in range(2):
        full_name = f"Test User {i}"
        email = f"test_user_{i}@example.com"
        is_admin = True if i % 2 == 0 else False

        new_user = await create_new_user(
            client=admin_client,
            full_name=full_name,
            email=email,
            is_admin=is_admin,
        )
        check_user_data(new_user, full_name, email, is_admin)

        user_data = await get_user(admin_client, new_user["uid"])
        check_user_data(user_data, full_name, email, is_admin)

    # Try to create a user with a mal-formatted email
    await create_new_user(
        client=admin_client,
        full_name="Invalid Email",
        email=INVALID_EMAIL,
        expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )

    # Try to create a user with invalid password lengths
    for password_length in (PASSWORD_MIN_LENGTH - 1, PASSWORD_MAX_LENGTH + 1):
        await create_new_user(
            client=admin_client,
            full_name="Invalid Password",
            password=random_password(length=password_length),
            expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


@pytest.mark.anyio
async def test_admin_update_user(
    client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    full_name = "Test Update"
    email = "test_update@example.com"
    password = random_password()
    is_admin = False

    new_user = await create_new_user(
        client=admin_client,
        full_name=full_name,
        email=email,
        password=password,
        is_admin=is_admin,
    )
    check_user_data(new_user, full_name, email, is_admin)

    uid = new_user["uid"]

    # Try to update full_name as admin
    await update_user(
        client=admin_client,
        uid=uid,
        full_name="New Name",
        expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )

    user_data = await get_user(admin_client, uid)
    check_user_data(user_data, full_name, email, is_admin)

    # Update email
    new_email = "updated_user@example.com"

    updated_user = await update_user(
        client=admin_client,
        uid=uid,
        email=new_email,
    )
    check_user_data(updated_user, full_name, new_email, is_admin)

    user_data = await get_user(admin_client, uid)
    check_user_data(user_data, full_name, new_email, is_admin)

    # Try to update the user with a mal-formatted email
    await update_user(
        client=admin_client,
        uid=uid,
        email=INVALID_EMAIL,
        expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )

    user_data = await get_user(admin_client, uid)
    check_user_data(user_data, full_name, new_email, is_admin)

    # Update is_admin
    for new_is_admin in (True, False):
        updated_user = await update_user(
            client=admin_client,
            uid=uid,
            is_admin=new_is_admin,
        )
        check_user_data(updated_user, full_name, new_email, new_is_admin)

        user_data = await get_user(admin_client, uid)
        check_user_data(user_data, full_name, new_email, new_is_admin)

    # Validate original password
    await validate_user_password(client, uid, new_email, password)

    # Update password
    new_password = random_password()

    updated_user = await update_user(
        client=admin_client,
        uid=uid,
        password=new_password,
    )
    check_user_data(updated_user, full_name, new_email, is_admin)

    await validate_user_password(client, uid, new_email, new_password)

    # Check the original password is no longer valid
    await validate_user_password(
        client,
        uid,
        new_email,
        password,
        expected_status=status.HTTP_401_UNAUTHORIZED,
    )

    # Try to update password with invalid lengths
    for password_length in (PASSWORD_MIN_LENGTH - 1, PASSWORD_MAX_LENGTH + 1):
        await update_user(
            client=admin_client,
            uid=uid,
            password=random_password(length=password_length),
            expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    await validate_user_password(client, uid, new_email, new_password)

    # Try to update the user without new values
    await update_user(
        client=admin_client,
        uid=uid,
        expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )

    # Try to update a nonexistent client
    await update_user(
        client=admin_client,
        uid=NONEXISTENT_USER_UID,
        password=random_password(),
        expected_status=status.HTTP_404_NOT_FOUND,
    )


@pytest.mark.anyio
async def test_admin_delete_user(admin_client: AsyncClient) -> None:
    users_to_delete = []

    for i in range(2):
        full_name = f"To Delete User {i}"
        is_admin = True if i % 2 == 0 else False

        new_user = await create_new_user(
            client=admin_client,
            full_name=full_name,
            is_admin=is_admin,
        )
        check_user_data(new_user, full_name, expected_is_admin=is_admin)

        user_data = await get_user(admin_client, new_user["uid"])
        check_user_data(user_data, full_name, expected_is_admin=is_admin)

        users_to_delete.append(user_data)

    # Check total users before deletion
    data = await get_all_users(admin_client)
    total_users = len(data)
    assert total_users > 0

    # Delete users
    for user_data in users_to_delete:
        uid = user_data["uid"]

        await delete_user(
            client=admin_client,
            uid=uid,
            expected_status=status.HTTP_204_NO_CONTENT,
        )

        await get_user(
            client=admin_client,
            uid=uid,
            expected_status=status.HTTP_400_BAD_REQUEST,
        )

        await delete_user(
            client=admin_client,
            uid=uid,
            expected_status=status.HTTP_400_BAD_REQUEST,
        )

    # Check total users after deletion
    data = await get_all_users(admin_client)
    assert len(data) == total_users - len(users_to_delete)

    # Try to delete a nonexistent client
    await delete_user(
        client=admin_client,
        uid=NONEXISTENT_USER_UID,
        expected_status=status.HTTP_404_NOT_FOUND,
    )


@pytest.mark.anyio
async def test_user_get(
    admin_client: AsyncClient,
    external_client: AsyncClient,
) -> None:
    for client, full_name, email in (
        (
            admin_client,
            settings.ADMIN_USER_FULL_NAME,
            settings.ADMIN_USER_EMAIL,
        ),
        (
            external_client,
            settings.EXTERNAL_USER_FULL_NAME,
            settings.EXTERNAL_USER_EMAIL,
        ),
    ):
        user_data = await get_user(client, SELF_UID)
        check_user_data(user_data, full_name, email, self_data=True)


@pytest.mark.anyio
async def test_update_user(
    client: AsyncClient,
    external_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    uid = SELF_UID
    full_name = settings.EXTERNAL_USER_FULL_NAME
    email = settings.EXTERNAL_USER_EMAIL
    password = settings.EXTERNAL_USER_PASSWORD
    original_user = await get_user(external_client, uid)
    check_user_data(original_user, full_name, email, self_data=True)

    # Try to update email and is_admin as regular user
    for new_email, is_admin in (("test@example.com", None), (None, True)):
        await update_user(
            client=external_client,
            uid=uid,
            email=new_email,
            is_admin=is_admin,
            expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    user_data = await get_user(external_client, uid)
    check_user_data(user_data, full_name, email, self_data=True)

    # Update full name
    new_full_name = "Updated Name"

    updated_user = await update_user(
        client=external_client,
        uid=uid,
        full_name=new_full_name,
    )
    check_user_data(updated_user, new_full_name, email, self_data=True)

    user_data = await get_user(external_client, uid)
    check_user_data(user_data, new_full_name, email, self_data=True)

    # Validate original password
    data = await get_all_users(admin_client)
    expected_uid = next(
        (user_data["uid"] for user_data in data if user_data["email"] == email),
        None,
    )

    await validate_user_password(client, expected_uid, email, password)

    # Update password
    new_password = random_password()

    updated_user = await update_user(
        client=external_client,
        uid=uid,
        password=new_password,
    )
    check_user_data(updated_user, new_full_name, email, self_data=True)

    external_client = await make_authenticated_client(
        external_client,
        email,
        new_password,
    )

    user_data = await get_user(external_client, uid)
    check_user_data(user_data, new_full_name, email, self_data=True)

    await validate_user_password(client, expected_uid, email, new_password)

    # Check the original password is no longer valid
    await validate_user_password(
        client,
        expected_uid,
        email,
        password,
        expected_status=status.HTTP_401_UNAUTHORIZED,
    )

    # Try to update password with invalid lengths
    for password_length in (PASSWORD_MIN_LENGTH - 1, PASSWORD_MAX_LENGTH + 1):
        await update_user(
            client=external_client,
            uid=uid,
            password=random_password(length=password_length),
            expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    await validate_user_password(client, expected_uid, email, new_password)

    # Try to update the user without new values
    await update_user(
        client=external_client,
        uid=uid,
        expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
