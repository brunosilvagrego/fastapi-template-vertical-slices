from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Item


async def create(
    db_session: AsyncSession,
    title: str,
    description: str,
    owner_id: int,
) -> Item:
    item = Item(title=title, description=description, owner_id=owner_id)

    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    return item


async def get(db_session: AsyncSession, id: int, owner_id: int) -> Item | None:
    stmt = select(Item).where(Item.id == id, Item.owner_id == owner_id)
    result = await db_session.execute(stmt)

    return result.scalar_one_or_none()


async def get_all(db_session: AsyncSession, owner_id: int) -> Sequence[Item]:
    stmt = select(Item).where(Item.owner_id == owner_id)
    result = await db_session.execute(stmt)

    return result.scalars().all()


async def update(
    db_session: AsyncSession,
    item: Item,
    title: str | None = None,
    description: str | None = None,
) -> Item:
    if all(param is None for param in (title, description)):
        return item

    if title is not None:
        item.title = title

    if description is not None:
        item.description = description

    await db_session.commit()
    await db_session.refresh(item)

    return item


async def delete(db_session: AsyncSession, item: Item) -> None:
    await db_session.delete(item)
    await db_session.commit()
