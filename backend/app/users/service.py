from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import utils
from app.users.models import User


async def create(
    db_session: AsyncSession,
    full_name: str,
    email: str,
    hashed_password: str,
    is_admin: bool = False,
) -> User:
    user = User(
        full_name=full_name,
        email=email,
        hashed_password=hashed_password,
        created_at=utils.now_utc(),
        is_admin=is_admin,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


async def get(db_session: AsyncSession, uid: str | None) -> User | None:
    if uid is None:
        return None

    stmt = select(User).where(User.uid == uid)
    result = await db_session.execute(stmt)

    return result.scalar_one_or_none()


async def get_by_email(db_session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    result = await db_session.execute(stmt)

    return result.scalar_one_or_none()


async def get_all(
    db_session: AsyncSession,
    active: bool = True,
) -> Sequence[User]:
    stmt = select(User)

    if active:
        stmt = stmt.where(User.deleted_at.is_(None))

    result = await db_session.execute(stmt)

    return result.scalars().all()


async def update(
    db_session: AsyncSession,
    user: User,
    email: str | None = None,
    full_name: str | None = None,
    hashed_password: str | None = None,
    is_admin: bool | None = None,
) -> User:
    updates = {
        "email": email,
        "full_name": full_name,
        "hashed_password": hashed_password,
        "is_admin": is_admin,
    }

    provided = {
        attribute: value
        for attribute, value in updates.items()
        if value is not None
    }

    if not provided:
        return user

    for attribute, value in provided.items():
        setattr(user, attribute, value)

    await db_session.commit()
    await db_session.refresh(user)

    return user


async def delete(db_session: AsyncSession, user: User) -> None:
    user.deleted_at = utils.now_utc()
    await db_session.commit()
