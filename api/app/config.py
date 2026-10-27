"""Application settings, loaded from environment / .env (see .env.example)."""
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Sylia API"
    env: str = "dev"

    # sqlite default lets the app + tests boot with zero infra; use Postgres in prod.
    database_url: str = "sqlite:///./sylia_dev.db"

    @field_validator("database_url")
    @classmethod
    def _psycopg3(cls, v: str) -> str:
        # Render/Heroku hand out postgres:// or postgresql://, which SQLAlchemy maps to
        # psycopg2; we ship psycopg 3.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    redis_url: str = "redis://localhost:6379/0"
    require_redis: bool = False          # prod with a separate worker: fail fast without Redis

    # public URL of this API (local upload URLs, OAuth callbacks)
    public_base_url: str = "http://localhost:8000"
    cors_origins: str = ""               # comma-separated; native apps don't need CORS

    jwt_secret: str = "dev-secret-change-me-dev-secret-change-me"
    encryption_key: str | None = None   # dedicated key for at-rest token encryption
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 30
    refresh_token_ttl_days: int = 30
    min_password_length: int = 8
    auth_rate_limit_per_min: int = 10    # per client IP, on signup/login/refresh
    apple_bundle_id: str = "com.sylia.stylist"   # Sign in with Apple audience
    admin_token: str | None = None       # guards /v1/admin (brand onboarding)

    # object storage
    s3_bucket: str = "sylia-dev"
    s3_endpoint_url: str | None = None            # set for Cloudflare R2
    upload_max_bytes: int = 15 * 1024 * 1024
    upload_url_ttl_s: int = 900

    # external services (keys injected in prod)
    anthropic_api_key: str | None = None
    openweather_api_key: str | None = None
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    revenuecat_webhook_secret: str | None = None  # Authorization header RevenueCat sends
    revenuecat_entitlement: str = "pro"
    google_client_id: str | None = None
    google_client_secret: str | None = None

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

    # brand insights only report cohorts at least this large (k-anonymity)
    insights_min_cohort: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
