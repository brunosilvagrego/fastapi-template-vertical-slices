from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import Token
from app.core.deps import get_db_session
from app.users.service import service_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/token",
    summary="Obtain an access token",
    description=(
        "Authenticate with email and password using the OAuth2 password flow. "
        "Returns a JWT bearer token that must be included in the "
        "`Authorization` header of subsequent requests as `Bearer <token>`."
    ),
    response_description="A JWT access token with its type.",
    responses={
        401: {"description": "Invalid credentials."},
    },
)
async def new_access_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db_session: AsyncSession = Depends(get_db_session),
) -> Token:
    """Authenticate a user and issue a JWT access token.

    Validates the provided email (submitted as `username`) and plaintext
    password against the stored hashed password. Raises HTTP 401 if either
    field is missing, if no user is found for the given email, or if the
    password does not match.

    Args:
        form: OAuth2 password-flow form containing `username` (email) and
            `password` fields.
        db_session: Async SQLAlchemy session injected by `get_db_session`.

    Returns:
        A :class:`Token` instance with `access_token` and `token_type`.

    Raises:
        HTTPException: 401 Unauthorized if credentials are absent or invalid.
    """
    return await service_user.authenticate(
        db_session=db_session,
        email=form.username,
        password=form.password,
    )
