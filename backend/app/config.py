from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), str(BASE_DIR / ".env")),
        extra="ignore",
    )

    gemini_api_key_1: str = ""
    gemini_api_key_2: str = ""
    gemini_api_key_3: str = ""
    gemini_model: str = "gemini-2.5-flash"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    search_api_key: str = ""

    database_url: str = f"sqlite:///{(BASE_DIR / 'cartmind.db').as_posix()}"
    frontend_url: str = "http://localhost:5173"
    store_url: str = "http://127.0.0.1:8000/store"
    playwright_headless: bool = True

    checkpoint_db: str = str(BASE_DIR / "checkpoints.db")
    knowledge_base_dir: str = str(ROOT_DIR / "knowledge_base" / "documents")

    @property
    def gemini_keys(self) -> list[str]:
        keys = [self.gemini_api_key_1, self.gemini_api_key_2, self.gemini_api_key_3]
        return [k.strip() for k in keys if k and k.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
