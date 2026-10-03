from pathlib import Path
import re

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect, text

from app.api import workspaces, action_items, auth, blog, decisions, meetings, notion, projects, risk, settings as settings_api, transcriptions
from app.core.config import settings
from app.api import workflow
from app.api import meeting_inputs
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

    @app.middleware("http")
    async def recover_stale_frontend_assets(request, call_next):
        # Previously cached HTML may still reference a removed entry bundle.
        path = request.url.path
        match = re.fullmatch(r"/assets/index-[\w-]+\.(js|css)", path)
        if match and not (FRONTEND_DIST / path.lstrip("/")).is_file():
            index = FRONTEND_DIST / "index.html"
            if index.is_file():
                current = re.search(
                    rf'(?:src|href)="(/assets/index-[\w-]+\.{match.group(1)})"',
                    index.read_text(encoding="utf-8"),
                )
                if current:
                    return RedirectResponse(
                        current.group(1), status_code=307,
                        headers={"Cache-Control": "no-store"},
                    )
        return await call_next(request)

    app.include_router(workspaces.router, prefix="/api")
    app.include_router(workflow.router, prefix="/api")
    app.include_router(meeting_inputs.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(blog.router, prefix="/api")
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
        ensure_legacy_columns()
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config("alembic.ini"), "head")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    async def web_app() -> FileResponse:
        frontend = FRONTEND_DIST / "index.html"
        # HTML points to hashed assets that change on every frontend build.
        # Do not reuse a cached document after those assets are replaced.
        return FileResponse(
            frontend if frontend.exists() else "app/static/index.html",
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    return app


def ensure_legacy_columns() -> None:
    """Add user ownership columns for existing SQLite prototypes without dropping data."""
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    targets = {
        "projects": "user_id INTEGER",
        "meetings": "user_id INTEGER",
        "action_items": "user_id INTEGER",
        "decisions": "user_id INTEGER",
    }
    with engine.begin() as connection:
        for table, definition in targets.items():
            if table not in inspector.get_table_names():
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "user_id" not in columns:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))
        if "meetings" in inspector.get_table_names():
            meeting_columns = {column["name"] for column in inspector.get_columns("meetings")}
            if "speaker_names" not in meeting_columns:
                connection.execute(text("ALTER TABLE meetings ADD COLUMN speaker_names JSON DEFAULT '{}'"))


app = create_app()
