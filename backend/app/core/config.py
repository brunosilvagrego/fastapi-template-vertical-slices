from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DB_HOST: str
    DB_PORT: int
    DB_DATABASE: str
    DB_USERNAME: str
    DB_PASSWORD: str

    # Security
    JWT_SECRET: str
    JWT_TOKEN_TYPE: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Default users
    ADMIN_CLIENT_NAME: str = "Admin"
    ADMIN_CLIENT_ID: str
    ADMIN_CLIENT_SECRET: str

    EXTERNAL_CLIENT_NAME: str = "Service A"
    EXTERNAL_CLIENT_ID: str
    EXTERNAL_CLIENT_SECRET: str


settings = Settings()
