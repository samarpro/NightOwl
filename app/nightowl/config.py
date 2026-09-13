"""NightOwl configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env"}

    # AWS Bedrock
    bedrock_region: str = "ap-southeast-2"
    bedrock_model: str = "au.anthropic.claude-haiku-4-5-20251001-v1:0"
    aws_bearer_token_bedrock: str = ""

    # Logfire
    logfire_token: str = ""

    # Composio
    composio_api_key: str = ""
    composio_user_id: str = "nightowl-default-user"

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
    max_spawn_depth: int = 1
    max_children_per_session: int = 3
    max_concurrent_bedrock_calls: int = 3
    hitl_timeout_seconds: int = 120

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    public_url: str = ""  # e.g. https://xyz.ngrok.io — needed for OAuth callbacks


settings = Settings()


def bedrock_provider():
    """Build a BedrockProvider with aggressive retry config (20 attempts, adaptive mode).

    Since the env var is now AWS_BEARER_TOKEN_BEDROCK, botocore picks up
    bearer token auth natively — we just build the client directly with retries.
    """
    import os

    import boto3
    from botocore.config import Config
    from pydantic_ai.providers.bedrock import BedrockProvider

    # Ensure botocore sees the bearer token from .env
    token = settings.aws_bearer_token_bedrock
    if token:
        os.environ.setdefault("AWS_BEARER_TOKEN_BEDROCK", token)

    retry_config = Config(
        retries={"max_attempts": 20, "mode": "adaptive"},
        read_timeout=300,
        connect_timeout=60,
    )
    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.bedrock_region,
        config=retry_config,
    )
    return BedrockProvider(bedrock_client=client)
