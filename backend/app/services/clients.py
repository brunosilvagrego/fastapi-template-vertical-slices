from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import utils
from app.models import Client


async def create(
    db_session: AsyncSession,
    name: str,
    oauth_id: str,
    oauth_secret_hash: str,
    is_admin: bool = False,
) -> Client:
    client = Client(
        name=name,
        created_at=utils.now_utc(),
        is_admin=is_admin,
        oauth_id=oauth_id,
        oauth_secret_hash=oauth_secret_hash,
    )

    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)

    return client


async def get(db_session: AsyncSession, id: int) -> Client | None:
    stmt = select(Client).where(Client.id == id)
    result = await db_session.execute(stmt)

    return result.scalar_one_or_none()


async def get_by_oauth_id(
    db_session: AsyncSession,
    oauth_id: str | None,
) -> Client | None:
    if oauth_id is None:
        return None

    stmt = select(Client).where(Client.oauth_id == oauth_id)
    result = await db_session.execute(stmt)

    return result.scalar_one_or_none()


async def get_all(
    db_session: AsyncSession,
    active: bool = True,
) -> Sequence[Client]:
    stmt = select(Client)

    if active:
        stmt = stmt.where(Client.deleted_at.is_(None))

    result = await db_session.execute(stmt)

    return result.scalars().all()


async def update(
    db_session: AsyncSession,
    client: Client,
    name: str | None = None,
    is_admin: bool | None = None,
    oauth_client_id: str | None = None,
    oauth_secret_hash: str | None = None,
) -> Client:
    if all(
        param is None
        for param in (name, is_admin, oauth_client_id, oauth_secret_hash)
    ):
        return client

    if name is not None:
        client.name = name

    if is_admin is not None:
        client.is_admin = is_admin

    if oauth_client_id is not None:
        client.oauth_id = oauth_client_id

    if oauth_secret_hash is not None:
        client.oauth_secret_hash = oauth_secret_hash

    await db_session.commit()
    await db_session.refresh(client)

    return client


async def delete(db_session: AsyncSession, client: Client) -> None:
    client.deleted_at = utils.now_utc()
    await db_session.commit()
