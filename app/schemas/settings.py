from pydantic import BaseModel, Field


class IntegrationSettingsRead(BaseModel):
    openai_configured: bool = False
    notion_api_configured: bool = False
    notion_database_configured: bool = False
    openai_connected: bool = False
    notion_connected: bool = False
    openai_key_masked: str | None = None
    notion_key_masked: str | None = None
    notion_database_id: str | None = None


class IntegrationSettingsUpdate(BaseModel):
    openai_api_key: str | None = Field(default=None, min_length=1)
    notion_api_key: str | None = Field(default=None, min_length=1)
    notion_database_id: str | None = Field(default=None, min_length=1)
