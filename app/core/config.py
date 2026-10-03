from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    app_env: str = "development"
    attachment_dir: str = "data/attachments"
    database_url: str = "sqlite:///./decisionflow.db"
    openai_api_key: str = ""
    transcription_model: str = "gpt-transcribe"
    diarization_model: str = "gpt-4o-transcribe-diarize"
    transcription_concurrency: int = 3
    ffmpeg_path: str = ""
    decision_analysis_model: str = "gpt-4o-mini"
    notion_api_key: str = ""
    notion_database_id: str = ""
    notion_api_version: str = "2026-03-11"
    secret_key: str = "change-me"
    encryption_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8001/api/auth/google/callback"
    frontend_url: str = "http://localhost:5173"
    ml_model_path: str = "app/ml/models/delay_risk.joblib"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_production_database(self):
        if self.app_env == "production" and not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("Production requires PostgreSQL DATABASE_URL.")
        if self.app_env == "production" and self.secret_key == "change-me":
            raise ValueError("Production requires a configured SECRET_KEY.")
        return self


settings = Settings()
