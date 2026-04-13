import logging
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Query, status
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenData
from app.core.database import SessionManager
from app.core.security import decode_access_token, oauth2_scheme
from app.items.models import Item
from app.items.service import service_item
from app.users.models import User
from app.users.service import service_user

logger = logging.getLogger(__name__)

EXPIRED_JWT = "Expired JWT"
INVALID_JWT = "Invalid JWT"


@dataclass
class PaginationParams:
    page: int
    per_page: int


def paginate(default_per_page: int = 50):
    def _pagination(
        page: int = Query(
            1,
            ge=1,
            description="Page number, starting from 1",
        ),
        per_page: int = Query(
            default_per_page,
            ge=1,
            le=50,
            description="Number of results per page",
        ),
    ) -> PaginationParams:
        return PaginationParams(page=page, per_page=per_page)

    return _pagination


async def get_db_session():
    async with SessionManager() as db_session:
        yield db_session


def check_user(user: User | None) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


def get_token_data(token: str = Depends(oauth2_scheme)) -> TokenData:
    try:
        token_data = decode_access_token(token)
    except ExpiredSignatureError:
        service_user.raise_unauthorized(EXPIRED_JWT)
    except (PyJWTError, ValidationError) as e:
        logger.warning(f"Invalid JWT: {e}")
        service_user.raise_unauthorized(INVALID_JWT)

    return token_data


async def get_current_user(
    token: TokenData = Depends(get_token_data),
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    if token.user_uid is None:
        logger.warning("Token does not contain user_uid")
        service_user.raise_unauthorized(INVALID_JWT)

    user = check_user(await service_user.get(db_session, uid=token.user_uid))

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.is_admin is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return current_user


async def get_user_by_uid(
    uid: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    user = check_user(await service_user.get(db_session, uid=uid))
    return user


async def get_item_by_id(
    id: int,
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> Item:
    item = await service_item.get(db_session, id=id, owner_uid=user.uid)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    return item
