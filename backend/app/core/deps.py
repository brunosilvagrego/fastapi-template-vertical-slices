import logging

import jwt
from fastapi import Depends, HTTPException, status
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenData
from app.core.config import settings
from app.core.database import SessionManager
from app.core.security import oauth2_scheme
from app.items import service as service_items
from app.items.models import Item
from app.users import service as service_users
from app.users.models import User

logger = logging.getLogger(__name__)

EXPIRED_JWT = "Expired JWT"
INVALID_JWT = "Invalid JWT"


async def get_db_session():
    async with SessionManager() as db_session:
        yield db_session


def raise_unauthorized(detail: str):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


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
        payload = jwt.decode(
            jwt=token,
            key=settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        token_data = TokenData(uid=payload.get("sub"))
    except ExpiredSignatureError:
        raise_unauthorized(EXPIRED_JWT)
    except (PyJWTError, ValidationError) as e:
        logger.warning(f"Invalid JWT: {e}")
        raise_unauthorized(INVALID_JWT)

    return token_data


async def get_current_user(
    token: TokenData = Depends(get_token_data),
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    if token.uid is None:
        logger.warning("Token does not contain uid")
        raise_unauthorized(INVALID_JWT)

    user = check_user(await service_users.get(db_session, token.uid))

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
    user = check_user(await service_users.get(db_session, uid))
    return user


async def get_item_by_id(
    id: int,
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> Item:
    item = await service_items.get(db_session, id, owner_uid=user.uid)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    return item
