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
)
async def create_item(
    create_schema: ItemCreate,
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> Item:
    return await service_item.new(db_session, user, create_schema)


@router.get("", response_model=list[ItemRead])
async def list_items(
    pagination: Annotated[PaginationParams, Depends(paginate())],
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> Sequence[Item]:
    return await service_item.get_multi(
        db_session,
        page=pagination.page,
        per_page=pagination.per_page,
        owner_uid=user.uid,
    )


@router.get("/{id}", response_model=ItemRead)
async def get_item(
    item: Item = Depends(get_item_by_id),
) -> Item:
    return item


@router.patch("/{id}", response_model=ItemRead)
async def update_item(
    update_schema: ItemUpdate,
    item: Item = Depends(get_item_by_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> Item | None:
    return await service_item.update_check(db_session, item, update_schema)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item: Item = Depends(get_item_by_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> None:
    await service_item.delete_check(db_session, item)
