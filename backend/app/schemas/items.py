from app.schemas.base import BaseModel


class ItemSchema(BaseModel):
    id: int
    title: str
    description: str


class ItemCreate(BaseModel):
    title: str
    description: str


class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
