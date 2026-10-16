import os
import sys
import tempfile
from pathlib import Path

# 앱 import 전에 테스트용 환경을 고정한다.
_tmp = Path(tempfile.mkdtemp(prefix="modu-sofa-test-"))
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{(_tmp / 'test.db').as_posix()}",
        "LOCAL_STORAGE_DIR": str(_tmp / "storage"),
        "DEV_AUTH_ENABLED": "true",
        "SUPABASE_URL": "",
        "SUPABASE_SERVICE_ROLE_KEY": "",
        "OPENAI_API_KEY": "",
        "STT_PROVIDER": "mock",
        "LLM_PROVIDER": "mock",
        "PUBLIC_API_BASE_URL": "http://testserver",
    }
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.core.config import settings  # noqa: E402

# 빈 환경변수는 무시되므로(.env 값이 쓰일 수 있음) 외부 연동 값은 직접 비운다.
for _k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET", "OPENAI_API_KEY"):
    setattr(settings, _k, "")

from app import models  # noqa: E402,F401
from app.db.session import Base, engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(scope="session")
def tmp_dir() -> Path:
    return _tmp
