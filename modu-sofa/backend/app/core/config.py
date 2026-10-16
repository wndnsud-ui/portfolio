from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # .env의 빈 값은 기본값을 쓴다
        extra="ignore",
    )

    # DB
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'dev.db').as_posix()}"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    STORAGE_BUCKET: str = "episodes"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_STT_MODEL: str = "gpt-4o-transcribe-diarize"
    OPENAI_LLM_MODEL: str = "gpt-4.1"

    # 제한
    MAX_UPLOAD_MB: int = 500
    MAX_DURATION_SEC: int = 5400
    STT_CHUNK_SEC: int = 1200
    STT_OVERLAP_SEC: int = 15
    STT_MAX_RETRIES: int = 3
    STT_CONCURRENCY: int = 2

    # 기타
    CORS_ORIGINS: str = "http://localhost:5173"
    SIGNED_URL_EXPIRES_SEC: int = 3600
    FFMPEG_PATH: str = ""
    FFPROBE_PATH: str = ""

    # 개발 모드: 키 없이 로컬에서 전체 흐름을 돌려볼 때 사용. 운영에서는 반드시 false.
    DEV_AUTH_ENABLED: bool = False
    LOCAL_STORAGE_DIR: str = str(BACKEND_DIR / "data" / "storage")
    LOCAL_STORAGE_SECRET: str = "dev-local-storage-secret"
    PUBLIC_API_BASE_URL: str = "http://localhost:8000"
    STT_PROVIDER: str = "auto"  # auto | openai | mock
    LLM_PROVIDER: str = "auto"  # auto | openai | mock

    # AI 시작음 (ElevenLabs Music)
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_MUSIC_MODEL: str = "music_v1"
    INTRO_PROVIDER: str = "auto"  # auto | elevenlabs | mock

    @property
    def use_supabase_storage(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_ROLE_KEY)

    @property
    def stt_provider(self) -> str:
        if self.STT_PROVIDER != "auto":
            return self.STT_PROVIDER
        return "openai" if self.OPENAI_API_KEY else "mock"

    @property
    def llm_provider(self) -> str:
        if self.LLM_PROVIDER != "auto":
            return self.LLM_PROVIDER
        return "openai" if self.OPENAI_API_KEY else "mock"

    @property
    def intro_provider(self) -> str:
        if self.INTRO_PROVIDER != "auto":
            return self.INTRO_PROVIDER
        return "elevenlabs" if self.ELEVENLABS_API_KEY else "mock"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# 분석을 시작할 때마다 .env에서 다시 읽는 항목 (서버 재시작 없이 키 연결/변경)
RELOADABLE = (
    "OPENAI_API_KEY", "OPENAI_STT_MODEL", "OPENAI_LLM_MODEL", "STT_PROVIDER", "LLM_PROVIDER",
    "ELEVENLABS_API_KEY", "ELEVENLABS_MUSIC_MODEL", "INTRO_PROVIDER",
)


def reload_analysis_settings() -> None:
    fresh = Settings()
    for name in RELOADABLE:
        setattr(settings, name, getattr(fresh, name))
