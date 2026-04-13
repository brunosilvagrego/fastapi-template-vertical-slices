from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import Token
from app.core.deps import get_db_session
from app.users.service import service_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token")
async def new_access_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db_session: AsyncSession = Depends(get_db_session),
) -> Token:
    return await service_user.authenticate(
        db_session=db_session,
        email=form.username,
        password=form.password,
    )
