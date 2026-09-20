from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        extra="ignore",
        populate_by_name=True,
    )

    polza_ai_base_url: str = "https://polza.ai/api/v1"
    polza_ai_api_key: str = ""
    polza_ai_model_name: str = "deepseek/deepseek-v4.1-flash"

    ui_locale: str = Field(default="ru", validation_alias=AliasChoices("EDITOR_UI_LOCALE", "UI_LOCALE"))
    data_dir: Path = Field(
        default=Path(__file__).resolve().parent.parent / "data",
        validation_alias=AliasChoices("EDITOR_DATA_DIR", "DATA_DIR"),
    )
    db_path: Optional[Path] = Field(
        default=None,
        validation_alias=AliasChoices("EDITOR_DB_PATH", "DB_PATH"),
    )
    critic_max_retries: int = Field(
        default=1,
        validation_alias=AliasChoices("EDITOR_CRITIC_MAX_RETRIES", "CRITIC_MAX_RETRIES"),
    )

    def resolved_db_path(self) -> Path:
        if self.db_path:
            return self.db_path
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "editor.db"


settings = Settings()
