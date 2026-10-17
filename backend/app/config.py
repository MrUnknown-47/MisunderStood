"""Configuration settings for MISUNDERSTOOD backend application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically load .env from project root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

class Settings:
    """Application settings loaded from environment."""

    APP_NAME: str = "MISUNDERSTOOD"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Database: Default to local SQLite, overridable by DATABASE_URL (e.g. Postgres)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./misunderstood.db")

    # CORS configuration
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
        if origin.strip()
    ]

    # AI Configuration (inherited by backend.ai module)
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "auto")
    AI_MODEL: str = os.getenv("AI_MODEL", "")
    AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "3000"))


settings = Settings()
