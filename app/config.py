#config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional

ENV_FILE_PATH = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        validate_default=False,
        env_file=ENV_FILE_PATH
    )

    # Postgres
    PG_USERNAME: str
    PG_PASSWORD: str
    PG_URL: str
    PG_NAME: str

    # Celery broker/backend
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672//"
    REDIS_URL: str = "redis://redis:6379/0"

    # Telegram (Telethon)
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_SESSION: str = "bot_session"

    # Telegram publish channel
    TELEGRAM_PUBLISH_CHANNEL: int = ""

    # OpenAI
    OPENAI_API_KEY: str = ""

settings = Settings()