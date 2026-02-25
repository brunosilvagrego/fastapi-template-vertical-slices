import pytest
from fastapi import status
from httpx import AsyncClient

API_CLIENTS_ENDPOINT = "/api/v1/clients"
API_CLIENT_ID_ENDPOINT = "/api/v1/clients/{id}"
NONEXISTENT_CLIENT_ID = 9999


async def check_endpoints_access(
    client: AsyncClient,
    headers: dict,
    expected_status: status,
) -> None:
    for request_func in [client.post, client.get]:
        response = await request_func(API_CLIENTS_ENDPOINT, headers=headers)
        assert response.status_code == expected_status

    client_id_url = API_CLIENT_ID_ENDPOINT.format(id=1)
    for request_func in [client.get, client.patch, client.delete]:
        response = await request_func(client_id_url, headers=headers)
        assert response.status_code == expected_status


def check_client_data(
    client_data: dict,
    expected_name: str | None = None,
    expected_is_admin: bool | None = None,
    deleted: bool = False,
    credentials: bool = False,
) -> None:
    assert isinstance(client_data, dict)
    assert isinstance(client_data.get("id"), int)
    assert isinstance(client_data.get("name"), str)
    assert isinstance(client_data.get("created_at"), str)
    assert isinstance(client_data.get("is_admin"), bool)
    assert "deleted_at" in client_data

    if expected_name is not None:
        assert client_data["name"] == expected_name

    if expected_is_admin is not None:
        assert client_data["is_admin"] == expected_is_admin

    deleted_at = client_data.get("deleted_at")

    if deleted:
        assert isinstance(deleted_at, (str))
    else:
        assert deleted_at is None

    client_id = client_data.get("client_id")
    client_secret = client_data.get("client_secret")

    if credentials:
        assert isinstance(client_id, str)
        assert isinstance(client_secret, str)
    else:
        assert client_id is None
        assert client_secret is None


async def create_new_client(
    client: AsyncClient,
    name: str,
    is_admin: bool,
) -> dict:
    response = await client.post(
        API_CLIENTS_ENDPOINT,
        json={"name": name, "is_admin": is_admin},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


async def get_client(
    client: AsyncClient,
    id: int,
    expected_status: status = status.HTTP_200_OK,
) -> dict | None:
    response = await client.get(API_CLIENT_ID_ENDPOINT.format(id=id))
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    return response.json()


async def update_client(
    client: AsyncClient,
    id: int,
    name: str | None = None,
    is_admin: bool | None = None,
    regenerate_credentials: bool | None = None,
    expected_status: status = status.HTTP_200_OK,
) -> dict:
    update_data = {}

    for key, value in (
        ("name", name),
        ("is_admin", is_admin),
        ("regenerate_credentials", regenerate_credentials),
    ):
        if value is not None:
            update_data[key] = value

    response = await client.patch(
        url=API_CLIENT_ID_ENDPOINT.format(id=id),
        json=update_data,
    )
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    return response.json()


async def delete_client(
    client: AsyncClient,
    id: int,
    expected_status: status = status.HTTP_204_NO_CONTENT,
) -> None:
    response = await client.delete(API_CLIENT_ID_ENDPOINT.format(id=id))
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
async def test_external_client_access(
    external_client: AsyncClient,
) -> None:
    await check_endpoints_access(
        external_client,
        headers={},
        expected_status=status.HTTP_403_FORBIDDEN,
    )


@pytest.mark.anyio
async def test_get_clients(admin_client: AsyncClient) -> None:
    response = await admin_client.get(API_CLIENTS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    for client_data in data:
        check_client_data(client_data)


@pytest.mark.anyio
async def test_get_client_by_id(admin_client: AsyncClient) -> None:
    for test_id in (1, 2, NONEXISTENT_CLIENT_ID):
        expected_status = (
            status.HTTP_404_NOT_FOUND
            if test_id == NONEXISTENT_CLIENT_ID
            else status.HTTP_200_OK
        )

        data = await get_client(
            client=admin_client,
            id=test_id,
            expected_status=expected_status,
        )

        if expected_status == status.HTTP_200_OK:
            check_client_data(data)


@pytest.mark.anyio
async def test_create_client(admin_client: AsyncClient) -> None:
    for name, is_admin in [("Service B", True), ("Service C", False)]:
        new_data = await create_new_client(
            client=admin_client,
            name=name,
            is_admin=is_admin,
        )
        check_client_data(new_data, name, is_admin, credentials=True)

        data = await get_client(admin_client, new_data["id"])
        check_client_data(data, name, is_admin)


@pytest.mark.anyio
async def test_update_client(admin_client: AsyncClient) -> None:
    name = "Service D"
    is_admin = False

    original_data = await create_new_client(
        client=admin_client,
        name=name,
        is_admin=is_admin,
    )
    check_client_data(original_data, name, is_admin, credentials=True)

    id = original_data["id"]

    # Update name
    new_name = "Updated Service"

    updated_data = await update_client(
        client=admin_client,
        id=id,
        name=new_name,
    )
    check_client_data(updated_data, new_name, is_admin)

    data = await get_client(admin_client, id)
    check_client_data(data, new_name, is_admin)

    # Update is_admin
    for is_admin in [True, False]:
        updated_data = await update_client(
            client=admin_client,
            id=id,
            is_admin=is_admin,
        )
        check_client_data(updated_data, new_name, is_admin)

        data = await get_client(admin_client, id)
        check_client_data(data, new_name, is_admin)

    # Update credentials
    updated_data = await update_client(
        client=admin_client,
        id=id,
        regenerate_credentials=True,
    )
    check_client_data(updated_data, new_name, is_admin, credentials=True)

    data = await get_client(admin_client, id)
    check_client_data(data, new_name, is_admin)

    # Try to update a nonexistent client
    await update_client(
        client=admin_client,
        id=NONEXISTENT_CLIENT_ID,
        name=new_name,
        expected_status=status.HTTP_404_NOT_FOUND,
    )


@pytest.mark.anyio
async def test_delete_client(admin_client: AsyncClient) -> None:
    clients_to_delete = []

    for name, is_admin in [
        ("Admin Service to Delete", True),
        ("Service to Delete", False),
    ]:
        new_data = await create_new_client(
            client=admin_client,
            name=name,
            is_admin=is_admin,
        )
        clients_to_delete.append(new_data)

        data = await get_client(admin_client, new_data["id"])
        check_client_data(data)

    for client in clients_to_delete:
        id = client["id"]

        await delete_client(
            client=admin_client,
            id=id,
            expected_status=status.HTTP_204_NO_CONTENT,
        )

        await get_client(
            client=admin_client,
            id=id,
            expected_status=status.HTTP_400_BAD_REQUEST,
        )

        await delete_client(
            client=admin_client,
            id=id,
            expected_status=status.HTTP_400_BAD_REQUEST,
        )

    # Try to delete a nonexistent client
    await delete_client(
        client=admin_client,
        id=NONEXISTENT_CLIENT_ID,
        expected_status=status.HTTP_404_NOT_FOUND,
    )
