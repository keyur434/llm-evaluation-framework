from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"
GOLDEN_PATH = DATA_DIR / "golden.json"
DEFAULT_DB = BACKEND_ROOT / "eval_history.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(BACKEND_ROOT.parent / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    eval_target_url: str = ""
    eval_target_model: str = "gpt-4o-mini"
    eval_target_api_key: str = ""
    eval_threshold: float = 0.80
    eval_regression: float = 0.05
    eval_concurrency: int = 8
    database_url: str = f"sqlite:///{DEFAULT_DB.as_posix()}"
    judge_model: str = "claude-sonnet-4-5"


@lru_cache
def get_settings() -> Settings:
    return Settings()
