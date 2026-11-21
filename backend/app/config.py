"""Environment-based configuration. Every setting comes from an environment variable."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    llm_api_keys: str = Field(default="", alias="LLM_API_KEYS")
    llm_model: str = Field(default="gemini/gemini-3.8-flash", alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")
    database_url: str = Field(default="sqlite:///./data/app.db", alias="DATABASE_URL")
    allowed_origins: str = Field(default="http://localhost:3000", alias="ALLOWED_ORIGINS")
    enable_failure_simulation: bool = Field(default=False, alias="ENABLE_FAILURE_SIMULATION")
    cache_enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    cache_type: str = Field(default="local", alias="CACHE_TYPE")  # "local" (memory) or "disk"
    cache_dir: str = Field(default="./data/llm_cache", alias="CACHE_DIR")
    default_system_prompt: str = Field(
        default="You are a helpful, concise AI assistant.", alias="DEFAULT_SYSTEM_PROMPT"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def api_keys(self) -> list[str]:
        return [k.strip() for k in self.llm_api_keys.split(",") if k.strip()]

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    return Settings()
