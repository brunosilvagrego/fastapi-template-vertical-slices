from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.schemas.items import ItemSchema


class Item(Base):
    __tablename__ = "item"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, unique=True)
    title: Mapped[str]
    description: Mapped[str]
    owner_id: Mapped[int] = mapped_column(ForeignKey("client.id"))

    def schema(self) -> ItemSchema:
        return ItemSchema(
            id=self.id,
            title=self.title,
            description=self.description,
        )
