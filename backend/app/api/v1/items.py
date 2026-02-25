from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_client,
    get_db_session,
    get_item_by_id,
)
from app.models.clients import Client
from app.models.items import Item
from app.schemas.items import (
    ItemCreate,
    ItemSchema,
    ItemUpdate,
)
from app.services import items as service_items

router = APIRouter(
    prefix="/items",
    tags=["Items"],
    dependencies=[Depends(get_current_client)],
)


@router.post(
    "",
    response_model=ItemSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_item(
    item_create: ItemCreate,
    client: Client = Depends(get_current_client),
    db_session: AsyncSession = Depends(get_db_session),
) -> ItemSchema:
    item = await service_items.create(
        db_session=db_session,
        title=item_create.title,
        description=item_create.description,
        owner_id=client.id,
    )

    return item.schema()


@router.get("", response_model=list[ItemSchema])
async def list_items(
    client: Client = Depends(get_current_client),
    db_session: AsyncSession = Depends(get_db_session),
) -> list[ItemSchema]:
    items = await service_items.get_all(
        db_session=db_session,
        owner_id=client.id,
    )

    return [item.schema() for item in items]


@router.get("/{id}", response_model=ItemSchema)
async def get_item(
    item: Item = Depends(get_item_by_id),
) -> ItemSchema:
    return item.schema()


@router.patch("/{id}", response_model=ItemSchema)
async def update_item(
    item_update: ItemUpdate,
    item: Item = Depends(get_item_by_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> ItemSchema:
    updated_item = await service_items.update(
        db_session=db_session,
        item=item,
        title=item_update.title,
        description=item_update.description,
    )

    return updated_item.schema()


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item: Item = Depends(get_item_by_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> None:
    await service_items.delete(db_session, item)
