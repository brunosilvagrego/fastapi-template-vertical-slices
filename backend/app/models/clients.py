from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.schemas.clients import ClientSchema


class Client(Base):
    __tablename__ = "client"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, unique=True)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_admin: Mapped[bool] = mapped_column(default=False)
    oauth_id: Mapped[str] = mapped_column(unique=True)
    oauth_secret_hash: Mapped[str]

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    def schema(self) -> ClientSchema:
        return ClientSchema(
            id=self.id,
            name=self.name,
            created_at=self.created_at,
            deleted_at=self.deleted_at,
            is_admin=self.is_admin,
        )
