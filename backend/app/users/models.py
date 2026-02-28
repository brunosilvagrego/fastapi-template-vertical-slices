from datetime import datetime

import shortuuid
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base
from app.users.schemas import UserRead, UserSchema


class User(Base):
    """Pluralized table name to avoid conflict with PostgreSQL default user
    table.
    """

    __tablename__ = "users"

    uid: Mapped[str] = mapped_column(primary_key=True, default=shortuuid.uuid)
    full_name: Mapped[str] = mapped_column(index=True)
    email: Mapped[str] = mapped_column(index=True, unique=True)
    hashed_password: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_admin: Mapped[bool] = mapped_column(default=False)

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    def schema(self) -> UserSchema:
        return UserSchema(
            uid=self.uid,
            full_name=self.full_name,
            email=self.email,
            created_at=self.created_at,
            deleted_at=self.deleted_at,
            is_admin=self.is_admin,
        )

    def schema_read(self) -> UserRead:
        return UserRead(
            full_name=self.full_name,
            email=self.email,
            joined_at=self.created_at,
        )
