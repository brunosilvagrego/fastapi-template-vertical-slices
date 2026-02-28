from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base
from app.items.schemas import ItemSchema


class Item(Base):
    __tablename__ = "item"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, unique=True)
    title: Mapped[str]
    description: Mapped[str]
    owner_uid: Mapped[str] = mapped_column(ForeignKey("users.uid"))

    def schema(self) -> ItemSchema:
        return ItemSchema(
            id=self.id,
            title=self.title,
            description=self.description,
        )
