import pytest
from app.core.config import settings
from app.core.consts import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.users.models import User
from app.users.service import service_user
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests import utils

API_ADMIN_USERS_ENDPOINT = "/api/v1/admin/users"
API_ADMIN_USERS_UID_ENDPOINT = "/api/v1/admin/users/{uid}"
API_USERS_ENDPOINT = "/api/v1/users/me"
SELF_UID = "me"
NONEXISTENT_USER_UID = "xyz"
USER_FULL_NAME = "Test User"
VALID_EMAIL = "user@example.com"
INVALID_EMAIL = "invalid_email"
VALID_PASSWORD = utils.random_password()
INVALID_PASSWORD_MIN = utils.random_password(PASSWORD_MIN_LENGTH - 1)
INVALID_PASSWORD_MAX = utils.random_password(PASSWORD_MAX_LENGTH + 1)


async def check_admin_endpoints_access(
    http_client: AsyncClient,
    headers: dict,
    expected_status: status,
) -> None:
    for request_func in [http_client.post, http_client.get]:
        response = await request_func(API_ADMIN_USERS_ENDPOINT, headers=headers)
        assert response.status_code == expected_status

    users_uid_url = API_ADMIN_USERS_UID_ENDPOINT.format(uid="test")
    for request_func in [
        http_client.get,
        http_client.patch,
        http_client.delete,
    ]:
        response = await request_func(users_uid_url, headers=headers)
        assert response.status_code == expected_status


async def check_user_endpoints_access(
    http_client: AsyncClient,
    headers: dict,
    expected_status: status,
) -> None:
    for request_func in [http_client.get, http_client.patch]:
        response = await request_func(API_USERS_ENDPOINT, headers=headers)
        assert response.status_code == expected_status


async def check_user_data(
    db_session: AsyncSession,
    user_data: dict,
    expected_full_name: str,
    expected_email: str,
    expected_is_admin: bool | None = None,
    deleted: bool = False,
    self_data: bool = False,
) -> None:
    assert isinstance(user_data, dict)

    full_name = user_data.get("full_name")
    assert isinstance(full_name, str)
    assert full_name == expected_full_name

    email = user_data.get("email")
    assert isinstance(email, str)
    assert email == expected_email

    created_at = user_data.get("created_at")
    assert isinstance(created_at, str)
    assert utils.is_iso_datetime(created_at)

    if self_data:
        return

    uid = user_data.get("uid")
    assert isinstance(uid, str)

    is_admin = user_data.get("is_admin")
    assert isinstance(is_admin, bool)
    assert is_admin == expected_is_admin

    assert "deleted_at" in user_data
    deleted_at = user_data.get("deleted_at")

    if deleted:
        assert isinstance(deleted_at, str)
        assert utils.is_iso_datetime(deleted_at)
    else:
        assert deleted_at is None

    db_user = await service_user.get(db_session, uid=uid)
    assert db_user.full_name == expected_full_name
    assert db_user.email == expected_email
    assert db_user.is_admin == expected_is_admin


async def check_users_list(
    db_session: AsyncSession,
    users_data: list[dict],
    expected_users: list[User],
) -> None:
    assert isinstance(users_data, list)
    assert len(users_data) == len(expected_users)

    for user_data, expected_user in zip(
        users_data,
        expected_users,
        strict=True,
    ):
        await check_user_data(
            db_session,
            user_data,
            expected_user.full_name,
            expected_user.email,
            expected_user.is_admin,
            deleted=True if expected_user.deleted_at is not None else False,
        )


async def create_user(
    http_client: AsyncClient,
    full_name: str | None,
    email: str | None,
    password: str | None,
    is_admin: bool | None,
    expected_status: status = status.HTTP_201_CREATED,
) -> dict | None:
    response = await http_client.post(
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


def get_user_url(uid: str):
    return (
        API_USERS_ENDPOINT
        if uid == SELF_UID
        else API_ADMIN_USERS_UID_ENDPOINT.format(uid=uid)
    )


async def get_user(
    http_client: AsyncClient,
    uid: str,
    expected_status: status = status.HTTP_200_OK,
) -> dict | None:
    url = get_user_url(uid)
    response = await http_client.get(url)
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    return response.json()


async def update_user(
    http_client: AsyncClient,
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
    response = await http_client.patch(url, json=update_data)
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    return response.json()


async def delete_user(
    http_client: AsyncClient,
    uid: str,
    expected_status: status = status.HTTP_204_NO_CONTENT,
) -> None:
    response = await http_client.delete(
        API_ADMIN_USERS_UID_ENDPOINT.format(uid=uid)
    )
    assert response.status_code == expected_status


@pytest.mark.anyio
async def test_users_endpoints_no_credentials(http_client: AsyncClient) -> None:
    for check_access_function in (
        check_admin_endpoints_access,
        check_user_endpoints_access,
    ):
        await check_access_function(
            http_client,
            headers={},
            expected_status=status.HTTP_401_UNAUTHORIZED,
        )


@pytest.mark.anyio
async def test_users_endpoints_invalid_token(http_client: AsyncClient) -> None:
    for check_access_function in (
        check_admin_endpoints_access,
        check_user_endpoints_access,
    ):
        await check_access_function(
            http_client,
            headers=utils.get_auth_header_invalid_token(),
            expected_status=status.HTTP_401_UNAUTHORIZED,
        )


@pytest.mark.anyio
async def test_users_endpoints_expired_token(http_client: AsyncClient) -> None:
    for check_access_function in (
        check_admin_endpoints_access,
        check_user_endpoints_access,
    ):
        await check_access_function(
            http_client,
            headers=utils.get_auth_header_expired_token(),
            expected_status=status.HTTP_401_UNAUTHORIZED,
        )


@pytest.mark.anyio
async def test_users_endpoints_external_access(
    http_client_external: AsyncClient,
) -> None:
    await check_admin_endpoints_access(
        http_client_external,
        headers={},
        expected_status=status.HTTP_403_FORBIDDEN,
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "full_name,email,password,is_admin,expected_status",
    [
        (
            USER_FULL_NAME,
            VALID_EMAIL,
            VALID_PASSWORD,
            True,
            status.HTTP_201_CREATED,
        ),
        (
            USER_FULL_NAME,
            VALID_EMAIL,
            VALID_PASSWORD,
            False,
            status.HTTP_201_CREATED,
        ),
        (
            "",
            VALID_EMAIL,
            VALID_PASSWORD,
            True,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            None,
            VALID_EMAIL,
            VALID_PASSWORD,
            False,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            5,
            VALID_EMAIL,
            VALID_PASSWORD,
            True,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            USER_FULL_NAME,
            INVALID_EMAIL,
            VALID_PASSWORD,
            False,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            USER_FULL_NAME,
            None,
            VALID_PASSWORD,
            True,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            USER_FULL_NAME,
            5,
            VALID_PASSWORD,
            False,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            USER_FULL_NAME,
            VALID_EMAIL,
            INVALID_PASSWORD_MIN,
            True,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            USER_FULL_NAME,
            VALID_EMAIL,
            INVALID_PASSWORD_MAX,
            True,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            USER_FULL_NAME,
            VALID_EMAIL,
            None,
            False,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            USER_FULL_NAME,
            VALID_EMAIL,
            5,
            True,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            USER_FULL_NAME,
            VALID_EMAIL,
            VALID_PASSWORD,
            None,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            USER_FULL_NAME,
            VALID_EMAIL,
            VALID_PASSWORD,
            5,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (None, None, None, None, status.HTTP_422_UNPROCESSABLE_CONTENT),
    ],
)
async def test_admin_create_user(
    db_session: AsyncSession,
    http_client_admin: AsyncClient,
    full_name: str | int | None,
    email: str | int | None,
    password: str | int | None,
    is_admin: bool | int | None,
    expected_status: status,
) -> None:
    user_data = await create_user(
        http_client_admin,
        full_name,
        email,
        password,
        is_admin,
        expected_status,
    )

    if expected_status == status.HTTP_201_CREATED:
        await check_user_data(db_session, user_data, full_name, email, is_admin)

        # Try to create a new user with the same email
        await create_user(
            http_client_admin,
            full_name,
            email,
            password,
            is_admin,
            expected_status=status.HTTP_409_CONFLICT,
        )


@pytest.mark.anyio
async def test_admin_list_users(
    db_session: AsyncSession,
    http_client_admin: AsyncClient,
) -> None:
    expected_users = []

    for email in (settings.ADMIN_USER_EMAIL, settings.EXTERNAL_USER_EMAIL):
        user = await service_user.get(db_session, email=email)
        assert user is not None
        expected_users.append(user)

    response = await http_client_admin.get(API_ADMIN_USERS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    # Check initial users list
    await check_users_list(
        db_session,
        users_data=response.json(),
        expected_users=expected_users,
    )

    # Check list after adding a new user
    new_user = await utils.new_user(db_session)
    expected_users.append(new_user)

    response = await http_client_admin.get(API_ADMIN_USERS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    await check_users_list(
        db_session,
        users_data=response.json(),
        expected_users=expected_users,
    )

    # Check list after deactivating a user
    await service_user.deactivate(db_session, new_user)

    response = await http_client_admin.get(API_ADMIN_USERS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    await check_users_list(
        db_session,
        users_data=response.json(),
        expected_users=expected_users[:2],
    )

    response = await http_client_admin.get(
        API_ADMIN_USERS_ENDPOINT,
        params={"active_only": False},
    )
    assert response.status_code == status.HTTP_200_OK

    await check_users_list(
        db_session,
        users_data=response.json(),
        expected_users=expected_users,
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "full_name,email,is_admin",
    [
        (settings.ADMIN_USER_FULL_NAME, settings.ADMIN_USER_EMAIL, True),
        (settings.EXTERNAL_USER_FULL_NAME, settings.EXTERNAL_USER_EMAIL, False),
    ],
)
async def test_admin_get_user(
    db_session: AsyncSession,
    http_client_admin: AsyncClient,
    full_name: str,
    email: str,
    is_admin: bool,
) -> None:
    db_user = await service_user.get(db_session, email=email)
    user_data = await get_user(http_client_admin, uid=db_user.uid)
    await check_user_data(db_session, user_data, full_name, email, is_admin)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "new_full_name,new_email,new_password,is_admin,expected_status",
    [
        (None, VALID_EMAIL, VALID_PASSWORD, True, status.HTTP_200_OK),
        (None, VALID_EMAIL, None, None, status.HTTP_200_OK),
        (None, None, VALID_PASSWORD, None, status.HTTP_200_OK),
        (None, None, None, True, status.HTTP_200_OK),
        (None, None, None, False, status.HTTP_200_OK),
        (
            None,
            INVALID_EMAIL,
            None,
            None,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (None, 5, None, None, status.HTTP_422_UNPROCESSABLE_CONTENT),
        (
            None,
            None,
            INVALID_PASSWORD_MIN,
            None,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            None,
            None,
            INVALID_PASSWORD_MAX,
            None,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (None, None, 5, None, status.HTTP_422_UNPROCESSABLE_CONTENT),
        (None, None, None, 5, status.HTTP_422_UNPROCESSABLE_CONTENT),
        (None, None, None, None, status.HTTP_422_UNPROCESSABLE_CONTENT),
        # Admin cannot update full_name
        ("New name", None, None, None, status.HTTP_422_UNPROCESSABLE_CONTENT),
    ],
)
async def test_admin_update_user(
    db_session: AsyncSession,
    http_client: AsyncClient,
    http_client_admin: AsyncClient,
    new_full_name: str | None,
    new_email: str | int | None,
    new_password: str | int | None,
    is_admin: bool | int | None,
    expected_status: status,
) -> None:
    password = utils.random_password()

    db_user = await utils.new_user(db_session, password=password)

    # Validate original password
    await utils.validate_user_password(
        http_client,
        db_user.uid,
        db_user.email,
        password,
    )

    # Update user
    updated_data = await update_user(
        http_client_admin,
        uid=db_user.uid,
        full_name=new_full_name,
        email=new_email,
        password=new_password,
        is_admin=is_admin,
        expected_status=expected_status,
    )

    if expected_status == status.HTTP_200_OK:
        await check_user_data(
            db_session,
            updated_data,
            expected_full_name=db_user.full_name,
            expected_email=new_email or db_user.email,
            expected_is_admin=is_admin or db_user.is_admin,
        )

        if new_password is not None:
            # Check that original password is no longer valid
            await utils.validate_user_password(
                http_client,
                db_user.uid,
                db_user.email,
                password,
                expected_status=status.HTTP_401_UNAUTHORIZED,
            )

            # Check that the new password is valid
            await utils.validate_user_password(
                http_client,
                db_user.uid,
                db_user.email,
                new_password,
            )


@pytest.mark.anyio
@pytest.mark.parametrize("is_admin", [(True), (False)])
async def test_admin_deactivate_user(
    db_session: AsyncSession,
    http_client_admin: AsyncClient,
    is_admin: bool,
) -> None:
    db_user = await utils.new_user(db_session, is_admin=is_admin)

    await get_user(
        http_client_admin,
        uid=db_user.uid,
        expected_status=status.HTTP_200_OK,
    )

    await delete_user(
        http_client_admin,
        uid=db_user.uid,
        expected_status=status.HTTP_204_NO_CONTENT,
    )

    await get_user(
        http_client_admin,
        uid=db_user.uid,
        expected_status=status.HTTP_400_BAD_REQUEST,
    )

    await delete_user(
        http_client_admin,
        uid=db_user.uid,
        expected_status=status.HTTP_400_BAD_REQUEST,
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "uid,expected_status",
    [
        (NONEXISTENT_USER_UID, status.HTTP_404_NOT_FOUND),
    ],
)
async def test_admin_endpoints_with_invalid_user_uids(
    http_client_admin: AsyncClient,
    uid: str | int,
    expected_status: status,
) -> None:
    await get_user(http_client_admin, uid, expected_status)

    await update_user(
        http_client_admin,
        uid,
        email=VALID_EMAIL,
        password=VALID_PASSWORD,
        is_admin=True,
        expected_status=expected_status,
    )

    await delete_user(http_client_admin, uid, expected_status)


@pytest.mark.anyio
async def test_get_user(
    db_session: AsyncSession,
    http_client_admin: AsyncClient,
    http_client_external: AsyncClient,
) -> None:
    for http_client, full_name, email in (
        (
            http_client_admin,
            settings.ADMIN_USER_FULL_NAME,
            settings.ADMIN_USER_EMAIL,
        ),
        (
            http_client_external,
            settings.EXTERNAL_USER_FULL_NAME,
            settings.EXTERNAL_USER_EMAIL,
        ),
    ):
        user_data = await get_user(http_client, SELF_UID)
        await check_user_data(
            db_session,
            user_data,
            full_name,
            email,
            self_data=True,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "new_full_name,new_email,new_password,is_admin,expected_status",
    [
        (USER_FULL_NAME, None, VALID_PASSWORD, None, status.HTTP_200_OK),
        (USER_FULL_NAME, None, None, None, status.HTTP_200_OK),
        (None, None, VALID_PASSWORD, None, status.HTTP_200_OK),
        (5, None, None, None, status.HTTP_422_UNPROCESSABLE_CONTENT),
        (
            None,
            None,
            INVALID_PASSWORD_MIN,
            None,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            None,
            None,
            INVALID_PASSWORD_MAX,
            None,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (
            None,
            None,
            5,
            None,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
        (None, None, None, None, status.HTTP_422_UNPROCESSABLE_CONTENT),
        # Non-admin users cannot update email or is_admin
        (None, VALID_EMAIL, None, None, status.HTTP_422_UNPROCESSABLE_CONTENT),
        (None, None, None, True, status.HTTP_422_UNPROCESSABLE_CONTENT),
    ],
)
async def test_update_user(
    db_session: AsyncSession,
    http_client: AsyncClient,
    http_client_external: AsyncClient,
    new_full_name: str | int | None,
    new_email: str | None,
    new_password: str | int | None,
    is_admin: bool | None,
    expected_status: status,
) -> None:
    db_user = await service_user.get(
        db_session,
        email=settings.EXTERNAL_USER_EMAIL,
    )

    # Validate original password
    await utils.validate_user_password(
        http_client,
        db_user.uid,
        db_user.email,
        settings.EXTERNAL_USER_PASSWORD,
    )

    # Update user
    updated_data = await update_user(
        http_client_external,
        uid=SELF_UID,
        full_name=new_full_name,
        email=new_email,
        password=new_password,
        is_admin=is_admin,
        expected_status=expected_status,
    )

    if expected_status == status.HTTP_200_OK:
        await check_user_data(
            db_session,
            updated_data,
            expected_full_name=new_full_name or db_user.full_name,
            expected_email=db_user.email,
            self_data=True,
        )

        if new_password is not None:
            # Check that original password is no longer valid
            await utils.validate_user_password(
                http_client,
                db_user.uid,
                db_user.email,
                password=settings.EXTERNAL_USER_PASSWORD,
                expected_status=status.HTTP_401_UNAUTHORIZED,
            )

            # Check that the new password is valid
            await utils.validate_user_password(
                http_client,
                db_user.uid,
                db_user.email,
                password=new_password,
            )
