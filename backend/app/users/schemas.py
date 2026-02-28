from datetime import datetime
from typing import Annotated, Self

from pydantic import ConfigDict, EmailStr, Field, model_validator

from app.core.consts import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.core.schemas import BaseModel

PasswordField = Annotated[
    str,
    Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH),
]


class UserSchema(BaseModel):
    uid: str
    full_name: str
    email: EmailStr
    created_at: datetime
    deleted_at: datetime | None
    is_admin: bool


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str
    email: EmailStr
    password: PasswordField
    is_admin: bool = False


class UserRead(BaseModel):
    full_name: str
    email: EmailStr
    joined_at: datetime


class UserUpdateAdmin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    password: PasswordField | None = None
    is_admin: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> Self:
        if all(
            param is None
            for param in (
                self.email,
                self.password,
                self.is_admin,
            )
        ):
            raise ValueError(
                "At least one of 'email', 'password' or 'is_admin' must be "
                "provided."
            )
        return self


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = None
    password: PasswordField | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> Self:
        if all(param is None for param in (self.full_name, self.password)):
            raise ValueError(
                "At least one of 'full_name' or 'password' must be provided."
            )
        return self
