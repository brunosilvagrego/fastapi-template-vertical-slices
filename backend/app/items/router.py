from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    PaginationParams,
    get_current_user,
    get_db_session,
    get_item_by_id,
    paginate,
)
from app.items.models import Item
from app.items.schemas import (
    ItemCreate,
    ItemRead,
    ItemUpdate,
)
from app.items.service import service_item
from app.users.models import User

router = APIRouter(
    prefix="/items",
    tags=["Items"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new item",
    description=(
        "Create a new item owned by the currently authenticated user. "
        "The item is associated with the user automatically from the "
        "`Authorization` header."
    ),
    response_description="The newly created item.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
    },
)
async def create_item(
    create_schema: ItemCreate,
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> Item:
    """Create a new item for the authenticated user.

    Args:
        create_schema: Validated payload describing the item to create.
        user: The currently authenticated user, resolved from the JWT token.
        db_session: Async SQLAlchemy session injected by `get_db_session`.

    Returns:
        The persisted :class:`Item` instance.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
    """
    return await service_item.new(db_session, user, create_schema)


@router.get(
    "",
    response_model=list[ItemRead],
    summary="List items",
    description=(
        "Return a paginated list of items belonging to the currently "
        "authenticated user. Use `page` and `per_page` query parameters to "
        "control pagination."
    ),
    response_description="A paginated list of items owned by the current user.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
    },
)
async def list_items(
    pagination: Annotated[PaginationParams, Depends(paginate())],
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> Sequence[Item]:
    """Return a paginated list of items owned by the authenticated user.

    Args:
        pagination: Resolved pagination parameters (`page`, `per_page`).
        user: The currently authenticated user, resolved from the JWT token.
        db_session: Async SQLAlchemy session injected by `get_db_session`.

    Returns:
        A sequence of :class:`Item` instances belonging to the current user.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
    """
    return await service_item.get_multi(
        db_session,
        page=pagination.page,
        per_page=pagination.per_page,
        owner_uid=user.uid,
    )


@router.get(
    "/{id}",
    response_model=ItemRead,
    summary="Get a single item",
    description="Retrieve a single item by its ID.",
    response_description="The requested item.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
        status.HTTP_404_NOT_FOUND: {"description": "Item not found."},
    },
)
async def get_item(
    item: Item = Depends(get_item_by_id),
) -> Item:
    """Retrieve a single item by its ID.

    Args:
        item: The :class:`Item` resolved by `get_item_by_id`. Raises 404 if
            no item exists with the given ID.

    Returns:
        The matching :class:`Item` instance.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
        HTTPException: 404 Not Found if no item matches the provided ID.
    """
    return item


@router.patch(
    "/{id}",
    response_model=ItemRead,
    summary="Update an item",
    description=(
        "Partially update an existing item. Only fields present in the request "
        "body are modified; omitted fields retain their current values."
    ),
    response_description="The updated item.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
        status.HTTP_404_NOT_FOUND: {"description": "Item not found."},
    },
)
async def update_item(
    update_schema: ItemUpdate,
    item: Item = Depends(get_item_by_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> Item | None:
    """Partially update an item after verifying ownership.

    Args:
        update_schema: Validated partial payload with fields to update.
        item: The :class:`Item` resolved by `get_item_by_id`. Raises 404 if
            no item exists with the given ID.
        db_session: Async SQLAlchemy session injected by `get_db_session`.

    Returns:
        The updated :class:`Item` instance, or ``None`` if the update produced
        no result (handled internally by the service).

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
        HTTPException: 404 Not Found if no item matches the provided ID.
    """
    return await service_item.update_check(db_session, item, update_schema)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
    description=(
        "Permanently delete an item by its ID. "
        "Only the owner of the item may delete it."
    ),
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Item deleted successfully."
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
        status.HTTP_404_NOT_FOUND: {"description": "Item not found."},
    },
)
async def delete_item(
    item: Item = Depends(get_item_by_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete an item after verifying ownership.

    Args:
        item: The :class:`Item` resolved by `get_item_by_id`. Raises 404 if
            no item exists with the given ID.
        db_session: Async SQLAlchemy session injected by `get_db_session`.

    Returns:
        ``None`` — the response body is empty (HTTP 204).

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
        HTTPException: 404 Not Found if no item matches the provided ID.
    """
    await service_item.delete_check(db_session, item)
