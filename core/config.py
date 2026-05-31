"""Configuration for game-hub using pydantic-settings pattern."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GAMEHUB_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    APP_NAME: str = "Play"
    APP_VERSION: str = "0.1.0"
    PORT: int = 3001

    DB_USER: str = "gamehub"
    DB_HOST: str = "postgres"
    DB_NAME: str = "gamehub"
    DB_PASSWORD: str = ""
    DB_PORT: int = 5432

    DATABASE_URL: str = ""

    CORS_ORIGINS: str = "https://play.silrod.org,http://localhost:3001"

    ANALYTICS_URL: str = ""
    ANALYTICS_ENABLED: bool = False

    def build_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()