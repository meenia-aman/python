from functools import lru_cache
import sys

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
    )

    DATABASE_URL: str = Field(min_length=1)


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()  # pyright: ignore[]
    except ValidationError as exc:
        print("Application cannot start: Invalid env configuration")
        print(exc)

        sys.exit(1)


settings = get_settings()
