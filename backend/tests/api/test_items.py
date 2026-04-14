import pytest
from app.core.config import settings
from app.items.service import service_item
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests import utils

API_ITEMS_ENDPOINT = "/api/v1/items"
API_ITEM_ID_ENDPOINT = "/api/v1/items/{id}"


async def check_endpoints_access(
    http_client: AsyncClient,
    headers: dict,
    expected_status: status,
) -> None:
    for request_func in [http_client.post, http_client.get]:
        response = await request_func(API_ITEMS_ENDPOINT, headers=headers)
        assert response.status_code == expected_status

    items_id_url = API_ITEM_ID_ENDPOINT.format(id=1)
    for request_func in [
        http_client.get,
        http_client.patch,
        http_client.delete,
    ]:
        response = await request_func(items_id_url, headers=headers)
        assert response.status_code == expected_status


async def check_item_data(
    db_session: AsyncSession,
    item_data: dict,
    expected_title: str,
    expected_description: str,
) -> None:
    assert isinstance(item_data, dict)

    item_id = item_data.get("id")
    assert isinstance(item_id, int)

    title = item_data.get("title")
    assert isinstance(title, str)
    assert title == expected_title

    description = item_data.get("description")
    assert isinstance(description, str)
    assert description == expected_description

    db_item = await service_item.get(db_session, id=item_id)
    assert db_item is not None
    assert db_item.title == expected_title
    assert db_item.description == expected_description


async def create_new_item(
    http_client: AsyncClient,
    title: str,
    description: str,
    expected_status: status = status.HTTP_201_CREATED,
) -> dict | None:
    response = await http_client.post(
        API_ITEMS_ENDPOINT,
        json={"title": title, "description": description},
    )
    assert response.status_code == expected_status

    if expected_status != status.HTTP_201_CREATED:
        return None

    return response.json()


async def get_item(
    http_client: AsyncClient,
    item_id: int,
    expected_status: status = status.HTTP_200_OK,
) -> dict | None:
    response = await http_client.get(API_ITEM_ID_ENDPOINT.format(id=item_id))
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    return response.json()


async def update_item(
    http_client: AsyncClient,
    item_id: int,
    title: str | None = None,
    description: str | None = None,
    expected_status: status = status.HTTP_200_OK,
) -> dict | None:
    update_data = {}

    for key, value in (("title", title), ("description", description)):
        if value is not None:
            update_data[key] = value

    response = await http_client.patch(
        url=API_ITEM_ID_ENDPOINT.format(id=item_id),
        json=update_data,
    )
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    return response.json()


async def delete_item(
    client: AsyncClient,
    item_id: int,
    expected_status: status = status.HTTP_204_NO_CONTENT,
) -> None:
    response = await client.delete(API_ITEM_ID_ENDPOINT.format(id=item_id))
    assert response.status_code == expected_status


@pytest.mark.anyio
async def test_item_endpoints_no_credentials(http_client: AsyncClient) -> None:
    await check_endpoints_access(
        http_client,
        headers={},
        expected_status=status.HTTP_401_UNAUTHORIZED,
    )


@pytest.mark.anyio
async def test_item_endpoints_invalid_token(http_client: AsyncClient) -> None:
    await check_endpoints_access(
        http_client,
        headers=utils.get_auth_header_invalid_token(),
        expected_status=status.HTTP_401_UNAUTHORIZED,
    )


@pytest.mark.anyio
async def test_item_endpoints_expired_token(http_client: AsyncClient) -> None:
    await check_endpoints_access(
        http_client,
        headers=utils.get_auth_header_expired_token(),
        expected_status=status.HTTP_401_UNAUTHORIZED,
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "title,description,expected_status",
    [
        ("Item A", "Description A", status.HTTP_201_CREATED),
        ("Item B", "Description B", status.HTTP_201_CREATED),
        ("", "Description C", status.HTTP_422_UNPROCESSABLE_CONTENT),
        (None, "Description C", status.HTTP_422_UNPROCESSABLE_CONTENT),
        (5, "Description C", status.HTTP_422_UNPROCESSABLE_CONTENT),
        ("Item C", "", status.HTTP_422_UNPROCESSABLE_CONTENT),
        ("Item C", None, status.HTTP_422_UNPROCESSABLE_CONTENT),
        ("Item C", 5, status.HTTP_422_UNPROCESSABLE_CONTENT),
    ],
)
async def test_create_item(
    db_session: AsyncSession,
    http_client_external: AsyncClient,
    title: str | int | None,
    description: str | int | None,
    expected_status: status,
) -> None:
    item_data = await create_new_item(
        http_client_external,
        title=title,
        description=description,
        expected_status=expected_status,
    )

    if expected_status == status.HTTP_201_CREATED:
        await check_item_data(db_session, item_data, title, description)


@pytest.mark.anyio
async def test_list_items(
    db_session: AsyncSession,
    http_client_external: AsyncClient,
    http_client_admin: AsyncClient,
) -> None:
    db_items = await utils.create_items(
        db_session,
        user_email=settings.EXTERNAL_USER_EMAIL,
        count=5,
    )

    response = await http_client_external.get(API_ITEMS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(db_items)

    for item_data, db_item in zip(data, db_items, strict=True):
        await check_item_data(
            db_session,
            item_data,
            db_item.title,
            db_item.description,
        )

    # Check user with no items
    response = await http_client_admin.get(API_ITEMS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.anyio
async def test_get_item(
    db_session: AsyncSession,
    http_client_external: AsyncClient,
    http_client_admin: AsyncClient,
) -> None:
    db_items = await utils.create_items(
        db_session,
        user_email=settings.EXTERNAL_USER_EMAIL,
        count=2,
    )

    for db_item in db_items:
        item_data = await get_item(
            http_client_external,
            item_id=db_item.id,
            expected_status=status.HTTP_200_OK,
        )
        await check_item_data(
            db_session,
            item_data,
            db_item.title,
            db_item.description,
        )

        # Try to get an item of another user
        await get_item(
            http_client_admin,
            item_id=db_item.id,
            expected_status=status.HTTP_404_NOT_FOUND,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "title,description,expected_status",
    [
        ("Item A", "Description A", status.HTTP_200_OK),
        ("Item B", None, status.HTTP_200_OK),
        (None, "Description B", status.HTTP_200_OK),
        ("", "Description C", status.HTTP_422_UNPROCESSABLE_CONTENT),
        (5, "Description C", status.HTTP_422_UNPROCESSABLE_CONTENT),
        ("Item C", "", status.HTTP_422_UNPROCESSABLE_CONTENT),
        ("Item C", 5, status.HTTP_422_UNPROCESSABLE_CONTENT),
        (None, None, status.HTTP_422_UNPROCESSABLE_CONTENT),
    ],
)
async def test_update_item(
    db_session: AsyncSession,
    http_client_external: AsyncClient,
    http_client_admin: AsyncClient,
    title: str | int | None,
    description: str | int | None,
    expected_status: status,
) -> None:
    db_item = await utils.create_item(
        db_session,
        user_email=settings.EXTERNAL_USER_EMAIL,
    )

    updated_data = await update_item(
        http_client_external,
        item_id=db_item.id,
        title=title,
        description=description,
        expected_status=expected_status,
    )

    if expected_status == status.HTTP_200_OK:
        await check_item_data(
            db_session,
            updated_data,
            title or db_item.title,
            description or db_item.description,
        )

        # Try to update an item of another user
        await update_item(
            http_client_admin,
            item_id=db_item.id,
            title="New Title",
            description="New Description",
            expected_status=status.HTTP_404_NOT_FOUND,
        )

        await check_item_data(
            db_session,
            updated_data,
            title or db_item.title,
            description or db_item.description,
        )


@pytest.mark.anyio
async def test_delete_item(
    db_session: AsyncSession,
    http_client_external: AsyncClient,
    http_client_admin: AsyncClient,
) -> None:
    db_item = await utils.create_item(
        db_session,
        user_email=settings.EXTERNAL_USER_EMAIL,
    )

    # Item found
    await get_item(
        http_client_external,
        item_id=db_item.id,
        expected_status=status.HTTP_200_OK,
    )

    # Try to delete an item of another user
    await delete_item(
        http_client_admin,
        item_id=db_item.id,
        expected_status=status.HTTP_404_NOT_FOUND,
    )

    # Delete item
    await delete_item(
        http_client_external,
        item_id=db_item.id,
        expected_status=status.HTTP_204_NO_CONTENT,
    )

    # Item not found
    await get_item(
        http_client_external,
        item_id=db_item.id,
        expected_status=status.HTTP_404_NOT_FOUND,
    )

    # Not possible to delete the same item twice
    await delete_item(
        http_client_external,
        item_id=db_item.id,
        expected_status=status.HTTP_404_NOT_FOUND,
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "item_id,expected_status",
    [
        (utils.NONEXISTENT_ID, status.HTTP_404_NOT_FOUND),
        ("invalid_id", status.HTTP_422_UNPROCESSABLE_CONTENT),
    ],
)
async def test_item_invalid_ids(
    http_client_external: AsyncClient,
    item_id: int | str,
    expected_status: status,
) -> None:
    await get_item(
        http_client_external,
        item_id=item_id,
        expected_status=expected_status,
    )

    await update_item(
        http_client_external,
        item_id=item_id,
        title="New Title",
        description="New Description",
        expected_status=expected_status,
    )

    await delete_item(
        http_client_external,
        item_id=item_id,
        expected_status=expected_status,
    )
