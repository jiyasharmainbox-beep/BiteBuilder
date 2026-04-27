from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    max_upload_size_bytes: int = 5 * 1024 * 1024
    posts_per_page: int = 10
    password_reset_token_expire_minutes: int = 30
    app_base_url: str = "http://localhost:8000"
    spoonacular_api_key: str = "fea2d12d9b6d455eaf2ef2996f6f7c2c"  # Required for /api/recipes/classify-image; set in .env


settings = Settings()  # type: ignore[call-arg] # Loaded from .env file