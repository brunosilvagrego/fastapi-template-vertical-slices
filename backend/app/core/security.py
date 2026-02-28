from copy import deepcopy
from datetime import timedelta

import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import utils
from app.core.config import settings
from app.core.consts import API_AUTH_ENDPOINT
from app.users import service as service_users
from app.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=API_AUTH_ENDPOINT)

password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


async def authenticate_user(
    db_session: AsyncSession,
    email: str | None,
    password: str | None,
) -> User | None:
    if email is None or password is None:
        return None

    user = await service_users.get_by_email(db_session, email)

    if user is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_access_token(data: dict) -> str:
    to_encode = deepcopy(data)

    expire = utils.now_utc() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt
