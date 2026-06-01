from typing import List, Optional, Union, Any
from pydantic import validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "NexusOS"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "secret" # In production, this should be a real secret
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # POSTGRES
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "nexusos"
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
    YELP_API_KEY: Optional[str] = None
    PINTEREST_ACCESS_TOKEN: Optional[str] = None

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
