from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BlogPostCreate(BaseModel):
    title: str
    summary: str | None = None
    content: str
    category: str | None = None
    tags: list[str] = []
    thumbnail_url: str | None = None
    status: str = "draft"
    source_type: str = "manual"
    source_id: int | None = None


class BlogPostUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    thumbnail_url: str | None = None
    status: str | None = None


class BlogPostRead(BlogPostCreate):
    id: int
    user_id: int
    slug: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlogGenerateRequest(BaseModel):
    source_type: str
    source_id: int
    content_type: str = "기술 블로그"
