from enum import StrEnum


class Environment(StrEnum):
    """Enum for supported environments."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
