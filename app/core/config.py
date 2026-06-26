import os
from typing import Optional
from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    APP_NAME: str = "StudioLive Backend"
    APP_ENV: str = "development"  # development, staging, production
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = Field(default="change_this_to_a_secure_random_string_in_production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 Days

    # Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/studiolive")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: str = "studiolive-media"
    AWS_S3_ENDPOINT_URL: Optional[str] = None  # Non-null for MinIO local dev
    AWS_SNS_ENABLED: bool = False

    # OTP
    OTP_EXPIRATION_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5

    # Payments
    RAZORPAY_API_KEY: str = "rzp_test_mockkey"
    RAZORPAY_API_SECRET: str = "mock_secret"
    RAZORPAY_WEBHOOK_SECRET: str = "mock_webhook_secret"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str]) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required")
        # Ensure it has asyncpg scheme if it is a postgresql URL
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


settings = Settings()
