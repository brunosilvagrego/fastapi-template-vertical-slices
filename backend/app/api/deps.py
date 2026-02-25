import logging

import jwt
from fastapi import Depends, HTTPException, status
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionManager
from app.core.security import oauth2_scheme
from app.models.clients import Client
from app.models.items import Item
from app.schemas.token import TokenData
from app.services import clients as service_clients
from app.services import items as service_items

logger = logging.getLogger(__name__)

EXPIRED_JWT = "Expired JWT"
INVALID_JWT = "Invalid JWT"


async def get_db_session():
    async with SessionManager() as db_session:
        yield db_session


def raise_unauthorized(detail: str):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def check_client(client: Client | None) -> Client:
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive client",
        )

    return client


def get_token_data(token: str = Depends(oauth2_scheme)) -> TokenData:
    try:
        payload = jwt.decode(
            jwt=token,
            key=settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        token_data = TokenData(client_id=payload.get("sub"))
    except ExpiredSignatureError:
        raise_unauthorized(EXPIRED_JWT)
    except (PyJWTError, ValidationError) as e:
        logger.warning(f"Invalid JWT: {e}")
        raise_unauthorized(INVALID_JWT)

    return token_data


async def get_current_client(
    token: TokenData = Depends(get_token_data),
    db_session: AsyncSession = Depends(get_db_session),
) -> Client:
    if token.client_id is None:
        logger.warning("Token does not contain client_id")
        raise_unauthorized(INVALID_JWT)

    client = check_client(
        await service_clients.get_by_oauth_id(db_session, token.client_id)
    )

    return client


async def get_current_admin_client(
    current_client: Client = Depends(get_current_client),
) -> Client:
    if not current_client.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return current_client


async def get_client_by_id(
    id: int,
    db_session: AsyncSession = Depends(get_db_session),
) -> Client:
    client = check_client(await service_clients.get(db_session, id))
    return client


async def get_item_by_id(
    id: int,
    client: Client = Depends(get_current_client),
    db_session: AsyncSession = Depends(get_db_session),
) -> Item:
    item = await service_items.get(db_session, id, owner_id=client.id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    return item
