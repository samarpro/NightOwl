"""NightOwl configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env"}

    # AWS Bedrock
    bedrock_region: str = "ap-southeast-2"
    bedrock_model: str = "au.anthropic.claude-opus-4-6-v1"
    bedrock_api_key: str = ""

    # Logfire
    logfire_token: str = ""

    # Composio
    composio_api_key: str = ""

    # Channel tokens
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/nightowl"

    # Session limits
    max_spawn_depth: int = 3
    max_children_per_session: int = 5
    hitl_timeout_seconds: int = 120

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
