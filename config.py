import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent


def env_file():
    """비밀값 파일 위치. 프로젝트 폴더가 iCloud에 있어서 기본은 iCloud 밖(~/Desktop/프로젝트/포트폴리오/env.txt)에 둔다.
    순서: ENV_FILE 환경변수 → ~/Desktop/프로젝트/포트폴리오/env.txt → 프로젝트 폴더의 .env"""
    if os.environ.get("ENV_FILE"):
        return Path(os.environ["ENV_FILE"]).expanduser()
    outside = Path.home() / "Desktop" / "프로젝트" / "포트폴리오" / "env.txt"
    return outside if outside.exists() else BASE_DIR / ".env"


load_dotenv(env_file())


def database_url():
    """DATABASE_URL이 있으면 Supabase(PostgreSQL), 없으면 로컬 SQLite."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{BASE_DIR / 'instance' / 'portfolio.db'}"
    # Supabase가 주는 주소(postgres://, postgresql://)를 psycopg 3 드라이버 주소로 맞춘다.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(32).hex()
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 한글을 \uXXXX로 바꾸지 않고 저장해야 본문 검색이 된다.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "json_serializer": lambda obj: json.dumps(obj, ensure_ascii=False),
    }
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "media")

    # 카카오 책 검색 (developers.kakao.com → 내 애플리케이션 → 앱 키 → REST API 키)
    KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "")

    # 노션 독서 DB 동기화 (notion.so/profile/integrations → 내부 통합 시크릿, DB 주소)
    NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
    NOTION_READING_DB = os.environ.get("NOTION_READING_DB", "")

    SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    WTF_CSRF_TIME_LIMIT = None
