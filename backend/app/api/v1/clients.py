from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_client_by_id,
    get_current_admin_client,
    get_db_session,
)
from app.core.security import new_client_credentials
from app.models.clients import Client
from app.schemas.clients import (
    ClientCreate,
    ClientCreateResponse,
    ClientSchema,
    ClientUpdate,
    ClientUpdateResponse,
)
from app.services import clients as service_clients

router = APIRouter(
    prefix="/clients",
    tags=["Clients"],
    dependencies=[Depends(get_current_admin_client)],
)


@router.post(
    "",
    response_model=ClientCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_client(
    client_create: ClientCreate,
    db_session: AsyncSession = Depends(get_db_session),
) -> ClientCreateResponse:
    client_id, client_secret, client_secret_hash = new_client_credentials()

    client = await service_clients.create(
        db_session=db_session,
        name=client_create.name,
        oauth_id=client_id,
        oauth_secret_hash=client_secret_hash,
        is_admin=client_create.is_admin,
    )

    return ClientCreateResponse(
        id=client.id,
        name=client.name,
        created_at=client.created_at,
        deleted_at=client.deleted_at,
        is_admin=client.is_admin,
        client_id=client.oauth_id,
        client_secret=client_secret,
    )


@router.get("", response_model=list[ClientSchema])
async def list_clients(
    db_session: AsyncSession = Depends(get_db_session),
) -> list[ClientSchema]:
    clients = await service_clients.get_all(db_session)

    return [client.schema() for client in clients]


@router.get("/{id}", response_model=ClientSchema)
async def get_client(
    client: Client = Depends(get_client_by_id),
) -> ClientSchema:
    return client.schema()


@router.patch("/{id}", response_model=ClientUpdateResponse)
async def update_client(
    client_update: ClientUpdate,
    client: Client = Depends(get_client_by_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> ClientUpdateResponse:
    new_client_id, new_client_secret, new_client_secret_hash = (
        new_client_credentials()
        if client_update.regenerate_credentials
        else (None, None, None)
    )

    updated_client = await service_clients.update(
        db_session=db_session,
        client=client,
        name=client_update.name,
        is_admin=client_update.is_admin,
        oauth_client_id=new_client_id,
        oauth_secret_hash=new_client_secret_hash,
    )

    return ClientUpdateResponse(
        id=updated_client.id,
        name=updated_client.name,
        created_at=updated_client.created_at,
        deleted_at=updated_client.deleted_at,
        is_admin=updated_client.is_admin,
        client_id=new_client_id,
        client_secret=new_client_secret,
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client: Client = Depends(get_client_by_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> None:
    await service_clients.delete(db_session, client)
