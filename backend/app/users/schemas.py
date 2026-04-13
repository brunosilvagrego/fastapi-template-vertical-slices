from datetime import datetime
from typing import Annotated

from pydantic import ConfigDict, EmailStr, Field

from app.core.consts import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.core.schemas import BaseModel, NonEmptyModel

UidField = Annotated[
    str,
    Field(description="User UID.", examples=["fWE3MZRWk4w2X9vBU2L98a"]),
]

FullNameField = Annotated[
    str,
    Field(description="User's full name.", examples=["John Smith"]),
]

EmailField = Annotated[
    EmailStr,
    Field(
        description="User's email address.",
        examples=["john.smith@example.com"],
    ),
]

IsAdminField = Annotated[
    bool,
    Field(
        description="Indicates if the user has administrator privileges.",
        examples=[True, False],
    ),
]

CreatedAtField = Annotated[
    datetime,
    Field(
        description="Timestamp of when the user was created.",
        examples=["2026-01-01T00:00:00Z"],
    ),
]

DeletedAtField = Annotated[
    datetime | None,
    Field(
        None,
        description="Timestamp of when the user was deleted.",
        examples=["2026-01-01T00:00:00Z", None],
    ),
]

PasswordField = Annotated[
    str,
    Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description="User's password.",
        examples=["secure_password"],
    ),
]

UpdatedPasswordField = Annotated[
    str,
    Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description="Updated password of the user.",
        examples=["updated_secure_password"],
    ),
]

HashedPasswordField = Annotated[
    str,
    Field(
        description="Hashed password of the user.",
        examples=["hashed_secure_password"],
    ),
]


class UserBase(BaseModel):
    uid: UidField
    full_name: FullNameField
    email: EmailField
    created_at: CreatedAtField
    deleted_at: DeletedAtField
    is_admin: IsAdminField


class UserCreateBase(BaseModel):
    full_name: FullNameField
    email: EmailField
    is_admin: IsAdminField = False

    model_config = ConfigDict(extra="forbid")


class UserCreate(UserCreateBase):
    password: PasswordField


class UserCreatePrivate(UserCreateBase):
    hashed_password: HashedPasswordField


class UserReadAdmin(UserBase):
    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    full_name: FullNameField
    email: EmailField
    created_at: CreatedAtField

    model_config = ConfigDict(from_attributes=True)


class UserUpdatePrivate(NonEmptyModel):
    full_name: FullNameField | None = None
    email: EmailField | None = None
    hashed_password: HashedPasswordField | None = None
    is_admin: IsAdminField | None = None

    model_config = ConfigDict(extra="forbid")


class UserUpdateAdmin(NonEmptyModel):
    email: EmailField | None = None
    password: UpdatedPasswordField | None = None
    is_admin: IsAdminField | None = None

    model_config = ConfigDict(extra="forbid")


class UserUpdate(NonEmptyModel):
    full_name: FullNameField | None = None
    password: UpdatedPasswordField | None = None

    model_config = ConfigDict(extra="forbid")
