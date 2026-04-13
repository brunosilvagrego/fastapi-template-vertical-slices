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
)
async def admin_create_user(
    create_schema: UserCreate,
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    return await service_user.new(db_session, create_schema)


@router_admin.get("", response_model=list[UserReadAdmin])
async def admin_list_users(
    pagination: Annotated[PaginationParams, Depends(paginate())],
    active_only: bool = Query(
        True,
        description="When true, only active clients are returned",
    ),
    db_session: AsyncSession = Depends(get_db_session),
) -> Sequence[User]:
    return await service_user.get_many(
        db_session,
        pagination.page,
        pagination.per_page,
        active_only,
    )


@router_admin.get("/{uid}", response_model=UserReadAdmin)
async def admin_get_user(
    user: User = Depends(get_user_by_uid),
) -> User:
    return user


@router_admin.patch("/{uid}", response_model=UserReadAdmin)
async def admin_update_user(
    update_schema: UserUpdateAdmin,
    user: User = Depends(get_user_by_uid),
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    return await service_user.private_update(db_session, user, update_schema)


@router_admin.delete("/{uid}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user(
    user: User = Depends(get_user_by_uid),
    db_session: AsyncSession = Depends(get_db_session),
) -> None:
    await service_user.deactivate(db_session, user)


@router.get("/me", response_model=UserRead)
async def get_user(
    user: User = Depends(get_current_user),
) -> User:
    return user


@router.patch("/me", response_model=UserRead)
async def update_user(
    update_schema: UserUpdate,
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    return await service_user.private_update(db_session, user, update_schema)
