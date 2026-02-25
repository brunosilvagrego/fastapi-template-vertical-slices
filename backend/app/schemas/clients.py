from datetime import datetime

from app.schemas.base import BaseModel


class ClientSchema(BaseModel):
    id: int
    name: str
    created_at: datetime
    deleted_at: datetime | None
    is_admin: bool


class ClientCreate(BaseModel):
    name: str
    is_admin: bool = False


class ClientCreateResponse(ClientSchema):
    client_id: str
    client_secret: str


class ClientUpdate(BaseModel):
    name: str | None = None
    is_admin: bool | None = None
    regenerate_credentials: bool = False


class ClientUpdateResponse(ClientSchema):
    client_id: str | None = None
    client_secret: str | None = None
