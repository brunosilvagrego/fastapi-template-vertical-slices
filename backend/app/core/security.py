from copy import deepcopy
from datetime import timedelta

import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from app.auth.schemas import TokenData
from app.core import utils
from app.core.config import settings
from app.core.consts import API_AUTH_ENDPOINT

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=API_AUTH_ENDPOINT)

password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def create_access_token(
    data: dict,
    expire_delta: timedelta | None = None,
) -> str:
    to_encode = deepcopy(data)

    if expire_delta is None:
        expire_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = utils.now_utc() + expire_delta

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    payload = jwt.decode(
        jwt=token,
        key=settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )

    return TokenData(user_uid=payload.get("sub"))
