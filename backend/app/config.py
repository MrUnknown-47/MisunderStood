from functools import lru_cache
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MISUNDERSTOOD"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./misunderstood.db"
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    AI_API_KEY: str = ""
    AI_MODEL: str = "gemini-1.5-pro"
    USE_MOCK_AI: bool = True
    SECRET_KEY: str = "misunderstood-development-secret-key-super-secure-change-in-prod"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
