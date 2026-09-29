from pydantic import BaseModel, Field


class IntegrationSettingsRead(BaseModel):
    openai_configured: bool
    notion_api_configured: bool
    notion_database_configured: bool


class IntegrationSettingsUpdate(BaseModel):
    openai_api_key: str | None = Field(default=None, min_length=1)
    notion_api_key: str | None = Field(default=None, min_length=1)
    notion_database_id: str | None = Field(default=None, min_length=1)

