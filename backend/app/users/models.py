from datetime import datetime

import shortuuid
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base
from app.core.utils import now_utc


class User(Base):
    __tablename__ = "users"

    uid: Mapped[str] = mapped_column(primary_key=True, default=shortuuid.uuid)
    full_name: Mapped[str] = mapped_column(index=True)
    email: Mapped[str] = mapped_column(index=True, unique=True)
    hashed_password: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_admin: Mapped[bool] = mapped_column(default=False)

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None
