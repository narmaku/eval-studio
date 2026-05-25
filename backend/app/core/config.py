from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "eval-studio"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./eval_studio.db"

    cors_origins: list[str] = ["http://localhost:5173"]

    litellm_api_key: str | None = None
    litellm_model: str = "gpt-4.1"

    auth_enabled: bool = False


settings = Settings()
