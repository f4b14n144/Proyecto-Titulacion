from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    AI_PROVIDER: str = "gemini"
    AI_MODEL: str = "gemini/gemini-1.5-flash"
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""

    IMAP_HOST: str = ""
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""
    REPLY_TO_DOMAIN: str = ""

    APP_NAME: str = "Sistema Informes UPS"
    ENVIRONMENT: str = "development"


settings = Settings()
