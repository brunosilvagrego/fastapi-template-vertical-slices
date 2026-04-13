import pydantic


class BaseModel(pydantic.BaseModel):
    """Base model for all schemas. General configurations may be added here."""


class NonEmptyModel(BaseModel):
    """Base model that requires at least one field to carry a non-``None``
    value.

    Useful for PATCH-style update schemas where an entirely empty payload
    (all fields ``None``) is semantically invalid and should be rejected
    before hitting the database layer.

    Raises:
        ValueError: During Pydantic model validation when every field in the
            model resolves to ``None``.

    Example:
        >>> class ItemUpdate(NonEmptyModel):
        ...     title: str | None = None
        ...     description: str | None = None
        >>> ItemUpdate()          # raises ValueError
        >>> ItemUpdate(title="x") # ok
    """

    @pydantic.model_validator(mode="after")
    def at_least_one_field(self):
        """Validate that at least one field has been supplied.

        Runs after all individual field validators have executed so that the
        full model state is available for inspection.

        Returns:
            The validated model instance unchanged.

        Raises:
            ValueError: When all field values are ``None``.
        """
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided")
        return self
