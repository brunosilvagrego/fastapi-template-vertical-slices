from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    get_current_admin,
    get_current_user,
    get_db_session,
    get_user_by_uid,
)
from app.core.security import get_password_hash
from app.users import service as service_users
from app.users.models import User
from app.users.schemas import (
    UserCreate,
    UserRead,
    UserSchema,
    UserUpdate,
    UserUpdateAdmin,
)

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
    response_model=UserSchema,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_user(
    user_create: UserCreate,
    db_session: AsyncSession = Depends(get_db_session),
) -> UserSchema:
    user = await service_users.create(
        db_session=db_session,
        full_name=user_create.full_name,
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
        is_admin=user_create.is_admin,
    )

    return user.schema()


@router_admin.get("", response_model=list[UserSchema])
async def admin_list_users(
    # TODO: add email query param
    db_session: AsyncSession = Depends(get_db_session),
) -> list[UserSchema]:
    users = await service_users.get_all(db_session)

    return [user.schema() for user in users]


@router_admin.get("/{uid}", response_model=UserSchema)
async def admin_get_user(
    user: User = Depends(get_user_by_uid),
) -> UserSchema:
    return user.schema()


@router_admin.patch("/{uid}", response_model=UserSchema)
async def admin_update_user(
    user_update: UserUpdateAdmin,
    user: User = Depends(get_user_by_uid),
    db_session: AsyncSession = Depends(get_db_session),
) -> UserSchema:
    user = await service_users.update(
        db_session=db_session,
        user=user,
        email=user_update.email,
        is_admin=user_update.is_admin,
    )

    return user.schema()


@router_admin.delete("/{uid}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user(
    user: User = Depends(get_user_by_uid),
    db_session: AsyncSession = Depends(get_db_session),
) -> None:
    await service_users.delete(db_session, user)


@router.get("/me", response_model=UserRead)
async def get_user(
    user: User = Depends(get_current_user),
) -> UserRead:
    return user.schema_read()


@router.patch("/me", response_model=UserRead)
async def update_user(
    user_update: UserUpdate,
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> UserRead:
    hashed_password = (
        get_password_hash(user_update.password)
        if user_update.password is not None
        else None
    )

    user = await service_users.update(
        db_session=db_session,
        user=user,
        full_name=user_update.full_name,
        hashed_password=hashed_password,
    )

    return user.schema_read()
