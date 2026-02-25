import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import settings
from app.core.security import (
    OAuth2ClientCredentialsRequestForm,
    authenticate_client,
    create_access_token,
)
from app.schemas.token import Token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token")
async def new_access_token(
    form: Annotated[OAuth2ClientCredentialsRequestForm, Depends()],
    db_session: AsyncSession = Depends(get_db_session),
) -> Token:
    client = await authenticate_client(
        db_session=db_session,
        client_id=form.client_id,
        client_secret=form.client_secret,
    )

    if client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect client_id or client_secret",
        )

    access_token = create_access_token(data={"sub": client.oauth_id})

    return Token(access_token=access_token, token_type=settings.JWT_TOKEN_TYPE)
