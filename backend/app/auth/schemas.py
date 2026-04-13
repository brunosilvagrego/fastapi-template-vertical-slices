from pydantic import ConfigDict, Field

from app.core.schemas import BaseModel


class Token(BaseModel):
    access_token: str = Field(
        description="JWT access token.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        description="Type of the token.",
        examples=["Bearer"],
    )

    model_config = ConfigDict(extra="forbid")


class TokenData(BaseModel):
    user_uid: str | None = Field(
        None,
        description="User UID extracted from the token.",
        examples=["fWE3MZRWk4w2X9vBU2L98a"],
    )

    model_config = ConfigDict(extra="forbid")
