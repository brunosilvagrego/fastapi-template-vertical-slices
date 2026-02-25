import pytest
from fastapi import status
from httpx import AsyncClient

API_ITEMS_ENDPOINT = "/api/v1/items"
API_ITEM_ID_ENDPOINT = "/api/v1/items/{id}"
DEFAULT_DESCRIPTION = "My item"
NONEXISTENT_ITEM_ID = 9999


async def create_new_item(
    client: AsyncClient,
    title: str,
    description: str,
) -> dict:
    response = await client.post(
        API_ITEMS_ENDPOINT,
        json={"title": title, "description": description},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def check_item_data(
    item_data: dict,
    expected_title: str | None = None,
    expected_description: str | None = None,
) -> None:
    assert isinstance(item_data, dict)
    assert isinstance(item_data.get("id"), int)
    assert isinstance(item_data.get("title"), str)
    assert isinstance(item_data.get("description"), str)

    if expected_title is not None:
        assert item_data["title"] == expected_title

    if expected_description is not None:
        assert item_data["description"] == expected_description


async def get_item(
    client: AsyncClient,
    item_id: int,
    expected_status: status = status.HTTP_200_OK,
) -> dict | None:
    response = await client.get(API_ITEM_ID_ENDPOINT.format(id=item_id))
    assert response.status_code == expected_status

    if expected_status != status.HTTP_200_OK:
        return None

    return response.json()


async def update_item(
    client: AsyncClient,
    item_id: int,
    title: str | None = None,
    description: bool | None = None,
    expected_status: status = status.HTTP_200_OK,
) -> dict:
    update_data = {}

    for key, value in (("title", title), ("description", description)):
        if value is not None:
            update_data[key] = value

    response = await client.patch(
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
async def test_create_item(external_client: AsyncClient) -> None:
    title = "Item 1"
    description = DEFAULT_DESCRIPTION

    new_data = await create_new_item(
        client=external_client,
        title=title,
        description=description,
    )
    check_item_data(new_data, title, description)

    data = await get_item(external_client, new_data["id"])
    check_item_data(data, title, description)


@pytest.mark.anyio
async def test_get_items(
    external_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    for i in range(2, 4):
        await create_new_item(
            client=external_client,
            title=f"Item {i}",
            description=DEFAULT_DESCRIPTION,
        )

    response = await external_client.get(API_ITEMS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    for item_data in data:
        check_item_data(item_data)

    # User with no items
    response = await admin_client.get(API_ITEMS_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.anyio
async def test_get_item_by_id(
    external_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    title = "Item 10"
    description = DEFAULT_DESCRIPTION

    original_data = await create_new_item(
        client=external_client,
        title=title,
        description=description,
    )
    check_item_data(original_data, title, description)

    item_id = original_data["id"]

    for test_id in (item_id, NONEXISTENT_ITEM_ID):
        expected_status = (
            status.HTTP_404_NOT_FOUND
            if test_id == NONEXISTENT_ITEM_ID
            else status.HTTP_200_OK
        )

        data = await get_item(
            client=external_client,
            item_id=test_id,
            expected_status=expected_status,
        )

        if expected_status == status.HTTP_200_OK:
            assert data == original_data
            check_item_data(data, title, description)

    # Try to get an item of another user
    await get_item(
        client=admin_client,
        item_id=item_id,
        expected_status=status.HTTP_404_NOT_FOUND,
    )


@pytest.mark.anyio
async def test_update_item(
    external_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    title = "Item 100"
    new_title = "Item C"
    description = DEFAULT_DESCRIPTION

    original_data = await create_new_item(
        client=external_client,
        title=title,
        description=description,
    )
    check_item_data(original_data, title, description)

    # Successful updates
    item_id = original_data["id"]
    last_data = original_data

    for title, description in (
        ("Item A", None),
        (None, "abc"),
        ("Item B", "def"),
        (None, None),
    ):
        updated_data = await update_item(
            client=external_client,
            item_id=item_id,
            title=title,
            description=description,
        )

        if title is None:
            title = last_data["title"]

        if description is None:
            description = last_data["description"]

        check_item_data(updated_data, title, description)

        data = await get_item(external_client, item_id)
        check_item_data(data, title, description)

        last_data = data

    # Try to update a nonexistent item
    await update_item(
        client=external_client,
        item_id=NONEXISTENT_ITEM_ID,
        title=new_title,
        description=DEFAULT_DESCRIPTION,
        expected_status=status.HTTP_404_NOT_FOUND,
    )

    # Try to update an item of another user
    await update_item(
        client=admin_client,
        item_id=item_id,
        title=new_title,
        description=DEFAULT_DESCRIPTION,
        expected_status=status.HTTP_404_NOT_FOUND,
    )


@pytest.mark.anyio
async def test_delete_item(
    external_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    items_to_delete = []

    for i in range(4, 6):
        new_data = await create_new_item(
            client=external_client,
            title=f"Item {i}",
            description=DEFAULT_DESCRIPTION,
        )
        items_to_delete.append(new_data)

        data = await get_item(external_client, new_data["id"])
        check_item_data(data)

    for item in items_to_delete:
        item_id = item["id"]

        # Try to delete an item of another user
        await delete_item(
            client=admin_client,
            item_id=item_id,
            expected_status=status.HTTP_404_NOT_FOUND,
        )

        # Delete item
        await delete_item(
            client=external_client,
            item_id=item_id,
            expected_status=status.HTTP_204_NO_CONTENT,
        )

        # Item not found
        await get_item(
            client=external_client,
            item_id=item_id,
            expected_status=status.HTTP_404_NOT_FOUND,
        )

        # Not possible to delete the same item twice
        await delete_item(
            client=external_client,
            item_id=item_id,
            expected_status=status.HTTP_404_NOT_FOUND,
        )

    # Try to delete a nonexistent item
    await delete_item(
        client=external_client,
        item_id=NONEXISTENT_ITEM_ID,
        expected_status=status.HTTP_404_NOT_FOUND,
    )
