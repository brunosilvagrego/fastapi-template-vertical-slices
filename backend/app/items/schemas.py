from typing import Annotated

from pydantic import ConfigDict, Field

from app.core.schemas import BaseModel, NonEmptyModel

ItemIdField = Annotated[
    int,
    Field(description="Unique identifier of the item.", examples=[1]),
]

ItemTitleField = Annotated[
    str,
    Field(
        min_length=1,
        description="Title of the item.",
        examples=["Sample Item"],
    ),
]

ItemDescriptionField = Annotated[
    str,
    Field(
        min_length=1,
        description="Description of the item.",
        examples=["This is a sample item description."],
    ),
]

ItemOwnerUIdField = Annotated[
    str,
    Field(
        description="UID of the owner of the item.",
        examples=["fWE3MZRWk4w2X9vBU2L98a"],
    ),
]


class ItemBase(BaseModel):
    title: ItemTitleField
    description: ItemDescriptionField


class ItemCreate(ItemBase):
    model_config = ConfigDict(extra="forbid")


class ItemCreatePrivate(ItemBase):
    owner_uid: ItemOwnerUIdField

    model_config = ConfigDict(extra="forbid")


class ItemRead(ItemBase):
    id: ItemIdField

    model_config = ConfigDict(from_attributes=True)


class ItemUpdate(NonEmptyModel):
    title: ItemTitleField | None = None
    description: ItemDescriptionField | None = None

    model_config = ConfigDict(extra="forbid")
