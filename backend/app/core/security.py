import secrets
from copy import deepcopy
from datetime import timedelta

import jwt
from fastapi import Form, HTTPException, Request
from fastapi.openapi.models import OAuthFlowClientCredentials, OAuthFlows
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED

from app.core import utils
from app.core.config import settings
from app.models import Client
from app.services import clients as service_clients


class Oauth2ClientCredentials(OAuth2):
    """Based on: https://github.com/fastapi/fastapi/discussions/7846"""

    def __init__(
        self,
        tokenUrl: str,  # noqa: N803
        scheme_name: str | None = None,
        scopes: dict | None = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlows(
            clientCredentials=OAuthFlowClientCredentials(
                tokenUrl=tokenUrl,
                scopes=scopes,
            )
        )
        super().__init__(
            flows=flows, scheme_name=scheme_name, auto_error=auto_error
        )

    async def __call__(self, request: Request) -> str | None:
        authorization: str | None = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != settings.JWT_TOKEN_TYPE:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={
                        "WWW-Authenticate": settings.JWT_TOKEN_TYPE.title()
                    },
                )
            else:
                return None
        return param


class OAuth2ClientCredentialsRequestForm:
    def __init__(
        self,
        grant_type: str = Form(None, pattern="client_credentials"),
        scope: str = Form(""),
        client_id: str | None = Form(None),
        client_secret: str | None = Form(None),
    ):
        self.grant_type = grant_type
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret


oauth2_scheme = Oauth2ClientCredentials(tokenUrl="/api/auth/token")

password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def generate_oauth_client_credentials() -> tuple[str, str]:
    return (secrets.token_urlsafe(16), secrets.token_urlsafe(32))


def new_client_credentials() -> tuple[str, str, str]:
    client_id, client_secret = generate_oauth_client_credentials()
    client_secret_hash = get_password_hash(client_secret)
    return client_id, client_secret, client_secret_hash


async def authenticate_client(
    db_session: AsyncSession,
    client_id: str | None,
    client_secret: str | None,
) -> Client | None:
    if client_id is None or client_secret is None:
        return None

    client = await service_clients.get_by_oauth_id(db_session, client_id)

    if client is None:
        return None

    if not verify_password(client_secret, client.oauth_secret_hash):
        return None

    return client


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
