from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    study_dir: Path
    activate_study_on_bootstrap: bool = False
    llm_provider: str = "aicredits_openai_compatible"
    aicredits_base_url: str | None = None
    aicredits_api_key: SecretStr | None = None
    llm_structured_output_mode: Literal["provider_native_json_schema", "json_text_fallback"] = "provider_native_json_schema"
    tutor_model: str | None = None
    judge_model: str | None = None
    tutor_temperature: float = Field(default=0.2, ge=0, le=2)
    judge_temperature: float = Field(default=0, ge=0, le=2)
    tutor_max_output_tokens: int = Field(default=2500, gt=0)
    judge_max_output_tokens: int = Field(default=6000, gt=0)
    llm_reasoning_effort: str | None = "low"
    llm_connect_timeout_seconds: int = Field(default=10, gt=0)
    llm_request_timeout_seconds: int = Field(default=120, gt=0)
    llm_stale_grace_seconds: int = Field(default=30, ge=0)
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, gt=0, le=65535)
    app_build_id: str = "dev"
    log_level: str = "INFO"
    idempotency_retention_seconds: int = Field(default=43200, gt=0)
    research_data_dir: Path = Path("/app/research-data")
    require_active_capture: bool = False
    active_capture_max_age_seconds: int = Field(default=300, gt=0)
    participant_study_title: str = "Learning study"
    participant_intro_text: str = "You will complete four guided learning sections. Each section contains a teaching conversation followed by an independent assessment."
    participant_privacy_text: str = "Privacy, consent, withdrawal, and data-use information will be provided here before participant deployment."
    participant_support_text: str = "Researcher contact and support instructions will be provided here."

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str) -> str:
        if not value.startswith("postgresql+"):
            raise ValueError("DATABASE_URL must use a PostgreSQL SQLAlchemy dialect")
        return value

    @model_validator(mode="after")
    def timeout_order(self) -> "Settings":
        if self.llm_stale_grace_seconds + self.llm_request_timeout_seconds <= self.llm_request_timeout_seconds:
            raise ValueError("LLM_STALE_GRACE_SECONDS must be positive")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
