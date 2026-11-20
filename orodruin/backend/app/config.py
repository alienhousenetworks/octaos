from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Public deployment hardening
    public_mode: bool = False
    chat_rate_per_min: int = 8

    # Database & Redis
    database_url: str = "postgresql+psycopg://osint:osint@localhost:5544/osint"
    redis_url: str = "redis://localhost:6379/0"
    gdelt_lastupdate_url: str = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    ingest_loop_seconds: int = 900

    # Security & Multi-Tenancy
    jwt_secret_key: str = "octaos-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    credential_encryption_key: str = ""

    # Fixed Local-First AI Configuration (no runtime Model Manager switching)
    ai_provider: str = "local"
    ai_base_url: str = "http://localhost:11434/v1"
    ai_text_model: str = "qwen3.5-4b"
    ai_vision_model: str = "gemma-4-e4b"
    image_model: str = "sd15"
    image_worker_url: str = "http://localhost:8101"
    video_model: str = "wan2.1-t2v-1.3b"
    video_worker_url: str = "http://localhost:8102"
    enable_external_llm: bool = False

    # Legacy Orodruin LLM compatibility aliases
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen3.5-4b"
    llm_api_key: str = ""

    # OSINT Data Source Keys (all optional)
    google_maps_key: str = ""
    firms_map_key: str = ""
    firms_source: str = "VIIRS_SNPP_NRT"
    acled_email: str = ""
    acled_password: str = ""
    acled_token_url: str = "https://acleddata.com/oauth/token"
    acled_read_url: str = "https://acleddata.com/api/acled/read"
    aisstream_key: str = ""
    sentinelhub_client_id: str = ""
    sentinelhub_client_secret: str = ""
    shodan_key: str = ""
    opensky_client_id: str = ""
    opensky_client_secret: str = ""
    windy_key: str = ""
    tomtom_key: str = ""
    openweather_key: str = ""


settings = Settings()
