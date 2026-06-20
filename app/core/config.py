from typing import List, Optional, Union, Any
from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "OctaOS"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "secret" # In production, this should be a real secret
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # POSTGRES
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "octaos"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> Any:
        if isinstance(v, str):
            return v
        return f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}/{values.get('POSTGRES_DB')}"

    # REDIS
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # LLM KEYS
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # PILOT CONFIG
    SHARED_CLAUDE_KEY: Optional[str] = None
    PILOT_BUDGET_LIMIT: float = 7000.0  # in INR

    # PUBLIC MEDIA — optional fallback for URL-based publishing; Meta/IG/LinkedIn use direct binary upload
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    MEDIA_UPLOAD_DIR: str = "uploads"

    # OAUTH — Meta (Facebook / Instagram)
    META_APP_ID: Optional[str] = None
    META_APP_SECRET: Optional[str] = None

    # OAUTH — LinkedIn
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None

    # OPTIONAL INTEGRATIONS

    PINTEREST_ACCESS_TOKEN: Optional[str] = None

    # SMTP & DEV SETTINGS
    DEV: bool = True
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    EMAIL_HOST: Optional[str] = None
    EMAIL_PORT: Optional[int] = None
    EMAIL_USE_TLS: bool = True
    EMAIL_HOST_USER: Optional[str] = None
    EMAIL_HOST_PASSWORD: Optional[str] = None
    DEFAULT_FROM_EMAIL: Optional[str] = None

    def __init__(self, **values: Any):
        super().__init__(**values)
        if self.EMAIL_HOST is not None:
            self.SMTP_HOST = self.EMAIL_HOST
        if self.EMAIL_PORT is not None:
            self.SMTP_PORT = self.EMAIL_PORT
        if self.EMAIL_HOST_USER is not None:
            self.SMTP_USER = self.EMAIL_HOST_USER
        if self.EMAIL_HOST_PASSWORD is not None:
            self.SMTP_PASSWORD = self.EMAIL_HOST_PASSWORD
        if self.DEFAULT_FROM_EMAIL is not None:
            self.SMTP_FROM = self.DEFAULT_FROM_EMAIL
        elif self.EMAIL_HOST_USER is not None:
            self.SMTP_FROM = self.EMAIL_HOST_USER

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore",
    )

settings = Settings()
