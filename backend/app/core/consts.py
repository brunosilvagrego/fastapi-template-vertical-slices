from enum import StrEnum


class Environment(StrEnum):
    """Enum for supported environments."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


API_AUTH_ENDPOINT = "/api/v1/auth/token"

PASSWORD_MIN_LENGTH = 16
PASSWORD_MAX_LENGTH = 32
