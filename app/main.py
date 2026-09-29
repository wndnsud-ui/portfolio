from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api import action_items, decisions, meetings, notion, projects, risk, settings as settings_api, transcriptions
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.session import engine


FRONTEND_DIST = Path("frontend/dist")


def create_app() -> FastAPI:
    app = FastAPI(title="DecisionFlow API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(projects.router, prefix="/api")
    app.include_router(meetings.router, prefix="/api")
    app.include_router(decisions.router, prefix="/api")
    app.include_router(action_items.router, prefix="/api")
    app.include_router(risk.router, prefix="/api")
    app.include_router(notion.router, prefix="/api")
    app.include_router(transcriptions.router, prefix="/api")
    app.include_router(settings_api.router, prefix="/api")
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.on_event("startup")
    def create_tables() -> None:
        Base.metadata.create_all(bind=engine)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    async def web_app() -> FileResponse:
        frontend = FRONTEND_DIST / "index.html"
        return FileResponse(frontend if frontend.exists() else "app/static/index.html")

    return app


app = create_app()
