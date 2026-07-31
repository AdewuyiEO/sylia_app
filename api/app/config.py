"""Application settings, loaded from environment / .env (see .env.example)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Sylia API"
    env: str = "dev"

    # sqlite default lets the app + tests boot with zero infra; use Postgres in prod.
    database_url: str = "sqlite:///./sylia_dev.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-secret-change-me"
    encryption_key: str | None = None   # dedicated key for at-rest token encryption
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 30
    refresh_token_ttl_days: int = 30

    # object storage
    s3_bucket: str = "sylia-dev"
    s3_endpoint_url: str | None = None            # set for Cloudflare R2

    # external services (keys injected in prod)
    anthropic_api_key: str | None = None
    openweather_api_key: str | None = None
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None

    # model tiers (spec §4.4): small/fast for explanations, larger for coach/onboarding
    # LLM provider: "anthropic" | "openai" | "none" (none => templated fallback)
    llm_provider: str = "anthropic"
    # Anthropic model tiers
    model_explanation: str = "claude-haiku-4-5-20251001"
    model_coach: str = "claude-sonnet-5"
    # OpenAI (used when llm_provider="openai")
    openai_api_key: str | None = None
    openai_model_explanation: str = "gpt-4o-mini"
    openai_model_coach: str = "gpt-4o"

    trial_days: int = 7
    subscription_price_usd: int = 19


@lru_cache
def get_settings() -> Settings:
    return Settings()
