from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from .paths import ROOT

VERSION = "0.1.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    cors_origins: str = "http://localhost:5173"
    admin_password: str = "change-me"
    jwt_secret: str = "change-me-long-random"
    explainer: str = "template"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = ""
    openaq_api_key: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
