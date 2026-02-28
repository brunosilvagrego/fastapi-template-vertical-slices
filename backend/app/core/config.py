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
    ADMIN_USER_FULL_NAME: str = "Admin"
    ADMIN_USER_EMAIL: str = "admin@example.com"
    ADMIN_USER_PASSWORD: str

    EXTERNAL_USER_FULL_NAME: str = "John Smith"
    EXTERNAL_USER_EMAIL: str = "jsmith@example.com"
    EXTERNAL_USER_PASSWORD: str


settings = Settings()
