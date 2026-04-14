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
    """Service layer for user management and authentication.

    Extends :class:`CRUDBase` with business logic for registration,
    authentication, profile updates, and soft-deletion. All database
    interactions are performed through the async SQLAlchemy session passed
    to each method, keeping the service stateless and easily testable.
    """

    def raise_unauthorized(
        self,
        detail: str = "Incorrect email or password",
    ) -> Never:
        """Raise an HTTP 401 Unauthorized exception.

        Centralises the construction of authentication error responses so
        that callers always produce a consistent status code and message
        format.

        Args:
            detail: Human-readable error message included in the response
                body. Defaults to a generic credential-failure message to
                avoid leaking whether the email or the password was wrong.

        Raises:
            HTTPException: Always raises 401 Unauthorized.
        """
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
        """Verify credentials and return a JWT access token.

        Looks up the user by email, verifies the plaintext password against
        the stored hash, and — if both checks pass — mints a signed JWT.
        Any failure (missing fields, unknown email, wrong password) raises
        HTTP 401 with a deliberately vague message to prevent user enumeration.

        Args:
            db_session: Async SQLAlchemy session used for the user lookup.
            email: The email address submitted by the client. May be ``None``
                if the form field was absent.
            password: The plaintext password submitted by the client. May be
                ``None`` if the form field was absent.

        Returns:
            A :class:`Token` containing `access_token` (signed JWT) and
            `token_type` (e.g. ``"bearer"``).

        Raises:
            HTTPException: 401 Unauthorized if `email` or `password` is
                ``None``, if no user is found for the email, or if the
                password does not match the stored hash.
        """
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
        """Create and persist a new user account.

        Hashes the plaintext password from `create_schema` before writing the
        record to the database. An email uniqueness constraint violation is
        surfaced as HTTP 409; all other unexpected errors become HTTP 500.

        Args:
            db_session: Async SQLAlchemy session used for the insert.
            create_schema: Public-facing schema with `full_name`, `email`,
                `password` (plaintext), and optional `is_admin` flag.

        Returns:
            The newly created and persisted :class:`User` instance.

        Raises:
            HTTPException: 409 Conflict if the email is already registered.
            HTTPException: 500 Internal Server Error on unexpected failures.
        """
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
        """Return a paginated list of users, optionally filtered to active ones.

        When `active_only` is ``True``, a ``WHERE deleted_at IS NULL`` filter
        is added so soft-deleted users are excluded from the results.

        Args:
            db_session: Async SQLAlchemy session used for the query.
            page: 1-based page number.
            per_page: Maximum number of records to return per page.
            active_only: When ``True``, only users whose `deleted_at` is
                ``NULL`` are included.

        Returns:
            A sequence of :class:`User` instances for the requested page.
        """
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
        """Partially update a user's profile fields.

        Accepts either a user-facing or admin-facing update schema. Only
        fields explicitly set in `update_schema` are written; ``None`` values
        are treated as *not provided* and leave the existing data unchanged.
        If a new plaintext password is included it is hashed before storage.

        An email uniqueness constraint violation is surfaced as HTTP 409; an
        ``None`` return from the underlying CRUD layer or any other unexpected
        error becomes HTTP 500.

        Args:
            db_session: Async SQLAlchemy session used for the update.
            user: The :class:`User` instance to update (already fetched from
                the database by the caller).
            update_schema: A :class:`UserUpdateAdmin` or :class:`UserUpdate`
                instance with the fields to change.

        Returns:
            The updated :class:`User` instance.

        Raises:
            HTTPException: 409 Conflict if the new email is already in use.
            HTTPException: 500 Internal Server Error if the update fails or
                returns ``None``.
        """

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
        """Soft-delete a user by stamping their `deleted_at` field.

        The user record is retained in the database, preserving referential
        integrity for any related records. The user is excluded from active
        user listings (``active_only=True``) after this operation.

        Args:
            db_session: Async SQLAlchemy session used to commit the change.
            user: The :class:`User` instance to deactivate.

        Returns:
            ``None``.
        """
        user.deleted_at = now_utc()
        await db_session.commit()
        await db_session.refresh(user)


service_user = ServiceUser(User)
