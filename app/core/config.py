from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    app_name: str = "Family AI Assistant"
    app_version: str = "0.1.0"
    
    database_url: str = "postgresql://postgres:postgres@localhost:5433/family_ai_assistant"
    database_echo: bool = False
    
    cors_origins: list[str] = ["*"]

@lru_cache
def get_settings() -> Settings:
    return Settings()

