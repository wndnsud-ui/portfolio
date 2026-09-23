from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(os.getenv("PODCAST_APP_HOME", Path(__file__).resolve().parents[1])).resolve()
DATA_DIR = ROOT / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
INDEX_PATH = DATA_DIR / "index.sqlite3"


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    transcribe_model: str
    analysis_model: str
    embedding_model: str


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        transcribe_model=os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1"),
        analysis_model=os.getenv("OPENAI_ANALYSIS_MODEL", "gpt-4o-mini"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )


def ensure_data_dirs() -> None:
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
