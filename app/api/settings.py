from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, UserSettings
from app.schemas.settings import IntegrationSettingsRead, IntegrationSettingsUpdate
from app.services.encryption_service import decrypt_secret, encrypt_secret, mask_secret

router = APIRouter(prefix="/settings", tags=["Settings"])


def get_or_create_settings(db: Session, user: User) -> UserSettings:
    if user.settings:
        return user.settings
    user.settings = UserSettings(user_id=user.id)
    db.add(user.settings)
    db.commit()
    db.refresh(user)
    return user.settings


def settings_status(user_settings: UserSettings) -> IntegrationSettingsRead:
    openai_key = decrypt_secret(user_settings.openai_api_key_encrypted)
    notion_key = decrypt_secret(user_settings.notion_api_key_encrypted)
    has_openai = bool(openai_key)
    has_notion_key = bool(notion_key)
    has_notion_db = bool(user_settings.notion_database_id)
    return IntegrationSettingsRead(
        openai_configured=has_openai,
        notion_api_configured=has_notion_key,
        notion_database_configured=has_notion_db,
        openai_connected=has_openai,
        notion_connected=has_notion_key and has_notion_db,
        openai_key_masked=mask_secret(openai_key),
        notion_key_masked=mask_secret(notion_key),
        notion_database_id=user_settings.notion_database_id,
    )


@router.get("", response_model=IntegrationSettingsRead)
async def read_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> IntegrationSettingsRead:
    return settings_status(get_or_create_settings(db, current_user))


@router.patch("", response_model=IntegrationSettingsRead)
@router.put("", response_model=IntegrationSettingsRead)
async def update_settings(payload: IntegrationSettingsUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> IntegrationSettingsRead:
    user_settings = get_or_create_settings(db, current_user)
    for field in ("openai_api_key", "notion_api_key", "notion_database_id"):
        value = getattr(payload, field)
        if value is None:
            continue
        normalized = value.strip()
        if field == "openai_api_key" and normalized:
            user_settings.openai_api_key_encrypted = encrypt_secret(normalized)
        elif field == "notion_api_key" and normalized:
            user_settings.notion_api_key_encrypted = encrypt_secret(normalized)
        elif field == "notion_database_id" and normalized:
            user_settings.notion_database_id = normalized
    db.commit()
    db.refresh(user_settings)
    return settings_status(user_settings)


@router.post("/test-openai")
async def test_openai(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, bool]:
    user_settings = get_or_create_settings(db, current_user)
    return {"ok": bool(decrypt_secret(user_settings.openai_api_key_encrypted))}


@router.post("/test-notion")
async def test_notion(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, bool]:
    user_settings = get_or_create_settings(db, current_user)
    return {"ok": bool(decrypt_secret(user_settings.notion_api_key_encrypted) and user_settings.notion_database_id)}
