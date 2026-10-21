from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/learning_support.db"
    secret_key: str = "replace-this-development-key-before-deployment"
    algorithm: str = "HS256"
    access_token_minutes: int = 60 * 12
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    adapter_url: str = ""
    adapter_api_key: str = ""
    practice_name: str = "Gabinete Pedagógico"
    cors_origins: str = (
        "http://localhost:5174,http://127.0.0.1:5174,http://localhost:3001,http://127.0.0.1:3001"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
