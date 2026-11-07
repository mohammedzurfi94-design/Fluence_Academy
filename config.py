from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # App Settings
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "fluence_academy_secure_key_default"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
    REQUIRED_TELEGRAM_CHANNEL: Optional[str] = "@YourChannelUsernameHere"

    # Database (Universal SQLAlchemy connection string)
    # Default is local SQLite async
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/fluence.db"

    # Admin Dashboard
    ADMIN_HOST: str = "0.0.0.0"
    ADMIN_PORT: int = 8000
    PORT: Optional[int] = None
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "adminpassword123"

    # AI Tutor
    AI_ENABLED: bool = True
    GEMINI_API_KEY: Optional[str] = "AQ.Ab8RN6LFDPHEQNAEPrx6x3PlcZFKYQl0wLs4ZJzsQ9xx0Dwo2Q"
    GROQ_API_KEY: Optional[str] = None

    # Notion Integration
    NOTION_API_TOKEN: Optional[str] = None
    NOTION_DATABASE_ID: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
