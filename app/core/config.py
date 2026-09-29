from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./decisionflow.db"
    openai_api_key: str = ""
    transcription_model: str = "gpt-transcribe"
    diarization_model: str = "gpt-4o-transcribe-diarize"
    transcription_concurrency: int = 3
    decision_analysis_model: str = "gpt-4o-mini"
    notion_api_key: str = ""
    notion_database_id: str = ""
    notion_api_version: str = "2026-03-11"
    secret_key: str = "change-me"
    ml_model_path: str = "app/ml/models/delay_risk.joblib"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
