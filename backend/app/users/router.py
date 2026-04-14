from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    PaginationParams,
    get_current_admin,
    get_current_user,
    get_db_session,
    get_user_by_uid,
    paginate,
)
from app.users.models import User
from app.users.schemas import (
    UserCreate,
    UserRead,
    UserReadAdmin,
    UserUpdate,
    UserUpdateAdmin,
)
from app.users.service import service_user

router_admin = APIRouter(
    prefix="/admin/users",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin)],
)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router_admin.post(
    "",
    response_model=UserReadAdmin,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user (admin)",
    description=(
        "Create a new user account. Available to administrators only. "
        "The `is_admin` flag may be set to grant the new user admin privileges."
    ),
    response_description=(
        "The newly created user with full admin-visible fields."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Caller does not have admin privileges."
        },
        status.HTTP_409_CONFLICT: {
            "description": "A user with the same email already exists."
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Unexpected server error during user creation."
        },
    },
)
async def admin_create_user(
    create_schema: UserCreate,
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    """Create a new user (admin endpoint).

    Hashes the provided plaintext password before persisting the user. Raises
    HTTP 409 if the email address is already registered.

    Args:
        create_schema: Validated payload containing `full_name`, `email`,
            `password`, and optionally `is_admin`.
        db_session: Async SQLAlchemy session injected by `get_db_session`.

    Returns:
        The persisted :class:`User` instance.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
        HTTPException: 403 Forbidden if the caller is not an admin.
        HTTPException: 409 Conflict if the email is already in use.
        HTTPException: 500 Internal Server Error on unexpected failures.
    """
    return await service_user.new(db_session, create_schema)


@router_admin.get(
    "",
    response_model=list[UserReadAdmin],
    summary="List users (admin)",
    description=(
        "Return a paginated list of users. By default only active users are "
        "returned. Set `active_only=false` to include soft-deleted users."
    ),
    response_description=(
        "A paginated list of users with full admin-visible fields."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Caller does not have admin privileges."
        },
    },
)
async def admin_list_users(
    pagination: Annotated[PaginationParams, Depends(paginate())],
    active_only: bool = Query(
        True,
        description="When true, only active clients are returned",
    ),
    db_session: AsyncSession = Depends(get_db_session),
) -> Sequence[User]:
    """Return a paginated list of users (admin endpoint).

    Args:
        pagination: Resolved pagination parameters (`page`, `per_page`).
        active_only: When ``True`` (default), exclude soft-deleted users from
            the results.
        db_session: Async SQLAlchemy session injected by `get_db_session`.

    Returns:
        A sequence of :class:`User` instances.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
        HTTPException: 403 Forbidden if the caller is not an admin.
    """
    return await service_user.get_many(
        db_session,
        pagination.page,
        pagination.per_page,
        active_only,
    )


@router_admin.get(
    "/{uid}",
    response_model=UserReadAdmin,
    summary="Get a user (admin)",
    description="Retrieve a single user by their UID.",
    response_description="The requested user with full admin-visible fields.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Caller does not have admin privileges."
        },
        status.HTTP_404_NOT_FOUND: {"description": "User not found."},
    },
)
async def admin_get_user(
    user: User = Depends(get_user_by_uid),
) -> User:
    """Retrieve a single user by UID (admin endpoint).

    Args:
        user: The :class:`User` resolved by `get_user_by_uid`. Raises 404 if
            no user exists with the given UID.

    Returns:
        The matching :class:`User` instance.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
        HTTPException: 403 Forbidden if the caller is not an admin.
        HTTPException: 404 Not Found if no user matches the provided UID.
    """
    return user


@router_admin.patch(
    "/{uid}",
    response_model=UserReadAdmin,
    summary="Update a user (admin)",
    description=(
        "Partially update any user's profile. Admins may modify all fields, "
        "including `is_admin`. Only fields present in the request body are "
        "changed."
    ),
    response_description="The updated user with full admin-visible fields.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Caller does not have admin privileges."
        },
        status.HTTP_404_NOT_FOUND: {"description": "User not found."},
        status.HTTP_409_CONFLICT: {
            "description": "A user with the same email already exists."
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Unexpected server error during update."
        },
    },
)
async def admin_update_user(
    update_schema: UserUpdateAdmin,
    user: User = Depends(get_user_by_uid),
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    """Partially update a user (admin endpoint).

    Admins may change any field including `is_admin`. A new plaintext password,
    if provided, is hashed before being stored.

    Args:
        update_schema: Validated partial payload with fields to update.
        user: The :class:`User` resolved by `get_user_by_uid`. Raises 404 if
            no user exists with the given UID.
        db_session: Async SQLAlchemy session injected by `get_db_session`.

    Returns:
        The updated :class:`User` instance.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
        HTTPException: 403 Forbidden if the caller is not an admin.
        HTTPException: 404 Not Found if no user matches the provided UID.
        HTTPException: 409 Conflict if the new email is already in use.
        HTTPException: 500 Internal Server Error on unexpected failures.
    """
    return await service_user.private_update(db_session, user, update_schema)


@router_admin.delete(
    "/{uid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user (admin)",
    description=(
        "Soft-delete a user by setting their `deleted_at` timestamp. "
        "The record is retained in the database but excluded from active user "
        "listings by default."
    ),
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "User deactivated successfully."
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Caller does not have admin privileges."
        },
        status.HTTP_404_NOT_FOUND: {"description": "User not found."},
    },
)
async def admin_delete_user(
    user: User = Depends(get_user_by_uid),
    db_session: AsyncSession = Depends(get_db_session),
) -> None:
    """Soft-delete (deactivate) a user (admin endpoint).

    Sets `deleted_at` to the current UTC time rather than removing the row,
    preserving data integrity for related records.

    Args:
        user: The :class:`User` resolved by `get_user_by_uid`. Raises 404 if
            no user exists with the given UID.
        db_session: Async SQLAlchemy session injected by `get_db_session`.

    Returns:
        ``None`` — the response body is empty (HTTP 204).

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
        HTTPException: 403 Forbidden if the caller is not an admin.
        HTTPException: 404 Not Found if no user matches the provided UID.
    """
    await service_user.deactivate(db_session, user)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the current user",
    description="Return the profile of the currently authenticated user.",
    response_description="The authenticated user's profile.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
    },
)
async def get_user(
    user: User = Depends(get_current_user),
) -> User:
    """Return the profile of the currently authenticated user.

    Args:
        user: The currently authenticated user, resolved from the JWT token.

    Returns:
        The :class:`User` instance for the caller.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
    """
    return user


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update the current user",
    description=(
        "Partially update the authenticated user's own profile. "
        "Only `full_name`, `email`, and `password` may be changed through "
        "this endpoint. Only fields present in the request body are modified."
    ),
    response_description="The updated user profile.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid authentication token."
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Unexpected server error during update."
        },
    },
)
async def update_user(
    update_schema: UserUpdate,
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    """Partially update the authenticated user's own profile.

    Users may update their `full_name`, `email`, and `password`. A new
    plaintext password, if provided, is hashed before being stored.

    Args:
        update_schema: Validated partial payload with fields to update.
        user: The currently authenticated user, resolved from the JWT token.
        db_session: Async SQLAlchemy session injected by `get_db_session`.

    Returns:
        The updated :class:`User` instance.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
        HTTPException: 500 Internal Server Error on unexpected failures.
    """
    return await service_user.private_update(db_session, user, update_schema)
