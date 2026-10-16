import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import reload_analysis_settings, settings
from app.core.errors import UserFacingError
from app.routers import (
    ai,
    edits,
    episodes,
    local_storage,
    speakers,
    transcripts,
    uploads,
)
from app.services.job_recovery_service import recover_stuck_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("modu-sofa")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.DEV_AUTH_ENABLED:
        log.warning("DEV_AUTH_ENABLED=true — 개발용 로그인이 열려 있습니다. 운영에서는 끄세요.")
    log.info(
        "storage=%s stt=%s llm=%s",
        "supabase" if settings.use_supabase_storage else "local",
        settings.stt_provider,
        settings.llm_provider,
    )
    recover_stuck_jobs()  # 서버 재시작으로 멈춘 작업 정리
    yield


app = FastAPI(title="모두의 소파 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)


@app.exception_handler(UserFacingError)
async def _user_error(_: Request, exc: UserFacingError):
    return JSONResponse(status_code=400, content={"detail": {"code": exc.code, "message": exc.message}})


app.include_router(episodes.router)
app.include_router(uploads.router)
app.include_router(transcripts.router)
app.include_router(speakers.router)
app.include_router(ai.router)
app.include_router(edits.router)
if not settings.use_supabase_storage:
    app.include_router(local_storage.router)


@app.get("/api/health")
def health():
    reload_analysis_settings()
    return {
        "ok": True,
        "storage": "supabase" if settings.use_supabase_storage else "local",
        "stt": settings.stt_provider,
        "llm": settings.llm_provider,
        "intro": settings.intro_provider,
        "dev_auth": settings.DEV_AUTH_ENABLED,
    }
