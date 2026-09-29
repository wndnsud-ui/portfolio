from pathlib import Path

from fastapi import APIRouter

from app.core.config import settings as app_settings
from app.core.exceptions import AppError
from app.schemas.settings import IntegrationSettingsRead, IntegrationSettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])
ENV_FILE = Path(".env")
FIELDS = {
    "openai_api_key": "OPENAI_API_KEY",
    "notion_api_key": "NOTION_API_KEY",
    "notion_database_id": "NOTION_DATABASE_ID",
}


def save_env_value(name: str, value: str) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    replacement = f"{name}={value}"
    for index, line in enumerate(lines):
        if line.strip().startswith(f"{name}="):
            lines[index] = replacement
            break
    else:
        lines.append(replacement)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def settings_status() -> IntegrationSettingsRead:
    return IntegrationSettingsRead(
        openai_configured=bool(app_settings.openai_api_key),
        notion_api_configured=bool(app_settings.notion_api_key),
        notion_database_configured=bool(app_settings.notion_database_id),
    )


@router.get("", response_model=IntegrationSettingsRead)
async def read_settings() -> IntegrationSettingsRead:
    return settings_status()


@router.put("", response_model=IntegrationSettingsRead)
async def update_settings(payload: IntegrationSettingsUpdate) -> IntegrationSettingsRead:
    ENV_FILE.touch(exist_ok=True)
    for field, env_name in FIELDS.items():
        value = getattr(payload, field)
        if value is None:
            continue
        normalized = value.strip()
        if "\n" in normalized or "\r" in normalized:
            raise AppError("INVALID_SETTING", "Settings values must be a single line.", 400)
        if normalized:
            save_env_value(env_name, normalized)
            setattr(app_settings, field, normalized)
    return settings_status()
