from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "eval-studio"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./eval_studio.db"

    cors_origins: str = "http://localhost:5173"

    litellm_api_key: str | None = None
    litellm_model: str | None = None

    auth_enabled: bool = False

    evaluator_config_dir: str = "config/evaluators"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
