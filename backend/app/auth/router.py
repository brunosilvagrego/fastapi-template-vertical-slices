from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import Token
from app.core.config import settings
from app.core.deps import get_db_session
from app.core.security import authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token")
async def new_access_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db_session: AsyncSession = Depends(get_db_session),
) -> Token:
    user = await authenticate_user(
        db_session=db_session,
        email=form.username,
        password=form.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(data={"sub": user.uid})

    return Token(access_token=access_token, token_type=settings.JWT_TOKEN_TYPE)
