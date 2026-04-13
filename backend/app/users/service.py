import logging
from collections.abc import Sequence
from typing import Never

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import Token
from app.core.config import settings
from app.core.consts import ENTITY_CREATION_ERROR
from app.core.crud import CRUDBase
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.core.utils import now_utc
from app.users.models import User
from app.users.schemas import (
    UserCreate,
    UserCreatePrivate,
    UserUpdate,
    UserUpdateAdmin,
    UserUpdatePrivate,
)

logger = logging.getLogger(__name__)


class ServiceUser(CRUDBase[User, UserCreatePrivate, UserUpdatePrivate]):
    def raise_unauthorized(
        self,
        detail: str = "Incorrect email or password",
    ) -> Never:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

    async def authenticate(
        self,
        db_session: AsyncSession,
        email: str | None,
        password: str | None,
    ) -> Token:
        if email is None or password is None:
            self.raise_unauthorized()

        user = await self.get(db_session, email=email)

        if user is None:
            self.raise_unauthorized()

        if not verify_password(password, user.hashed_password):
            self.raise_unauthorized()

        access_token = create_access_token(data={"sub": user.uid})

        return Token(
            access_token=access_token,
            token_type=settings.JWT_TOKEN_TYPE,
        )

    async def new(
        self,
        db_session: AsyncSession,
        create_schema: UserCreate,
    ) -> User:
        try:
            user = await self.create(
                db_session=db_session,
                create_schema=UserCreatePrivate(
                    full_name=create_schema.full_name,
                    email=create_schema.email,
                    hashed_password=get_password_hash(create_schema.password),
                    is_admin=create_schema.is_admin,
                ),
            )
        except Exception as err:  # noqa: BLE001
            logger.error(
                ENTITY_CREATION_ERROR,
                User.__name__,
                create_schema.model_dump_json(),
                err,
            )

            if isinstance(err, IntegrityError):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A User with the same email already exists.",
                ) from None

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register client.",
            ) from None

        return user

    async def get_many(
        self,
        db_session: AsyncSession,
        page: int,
        per_page: int,
        active_only: bool,
    ) -> Sequence[User]:
        filters = [User.deleted_at.is_(None)] if active_only else []

        return await self.get_multi(
            db_session,
            *filters,
            page=page,
            per_page=per_page,
        )

    async def private_update(
        self,
        db_session: AsyncSession,
        user: User,
        update_schema: UserUpdateAdmin | UserUpdate,
    ) -> User:
        def _failed_user_update() -> Never:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user.",
            ) from None

        try:
            full_name = getattr(update_schema, "full_name", None)
            email = getattr(update_schema, "email", None)
            password = getattr(update_schema, "password", None)
            hashed_password = get_password_hash(password) if password else None
            is_admin = getattr(update_schema, "is_admin", None)

            updated_user = await self.update(
                db_session,
                db_object=user,
                update_schema=UserUpdatePrivate(
                    full_name=full_name,
                    email=email,
                    hashed_password=hashed_password,
                    is_admin=is_admin,
                ),
            )

            if updated_user is None:
                _failed_user_update()

        except Exception as err:  # noqa: BLE001
            logger.error(
                "Failed to update user '%s' with schema %s: %s",
                user.uid,
                update_schema.model_dump_json(),
                err,
            )

            if isinstance(err, IntegrityError):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A User with the same email already exists.",
                ) from None

            _failed_user_update()

        return updated_user

    async def deactivate(
        self,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        user.deleted_at = now_utc()
        await db_session.commit()
        await db_session.refresh(user)


service_user = ServiceUser(User)
