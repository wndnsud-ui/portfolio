"""baseline: 커밋 3f9f1ac 시점의 테이블 8개 (SQLite에서 create_all + 수동 ALTER로 만들던 구조)

기존 로컬 DB는 `flask db stamp 0001_baseline` 후 `flask db upgrade`.
빈 DB(Supabase)는 `flask db upgrade`만 하면 된다.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-07
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def timestamps():
    return [sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime())]


def upgrade():
    op.create_table(
        "profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("headline", sa.String(240), nullable=False),
        sa.Column("intro", sa.Text()),
        sa.Column("email", sa.String(160)),
        sa.Column("github", sa.String(240)),
        sa.Column("notion", sa.String(240)),
        *timestamps(),
    )
    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("subtitle", sa.String(240)),
        sa.Column("description", sa.Text()),
        sa.Column("problem", sa.Text()),
        sa.Column("role", sa.Text()),
        sa.Column("process", sa.Text()),
        sa.Column("action", sa.Text()),
        sa.Column("trouble", sa.Text()),
        sa.Column("solution", sa.Text()),
        sa.Column("result", sa.Text()),
        sa.Column("insight", sa.Text()),
        sa.Column("tech_stack", sa.String(400)),
        sa.Column("thumbnail", sa.String(240)),
        sa.Column("github_url", sa.String(240)),
        sa.Column("notion_url", sa.String(240)),
        *timestamps(),
        sa.Column("demo_url", sa.String(240), server_default=""),
    )
    op.create_table(
        "experience",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company", sa.String(160), nullable=False),
        sa.Column("position", sa.String(160)),
        sa.Column("start_date", sa.String(40)),
        sa.Column("end_date", sa.String(40)),
        sa.Column("description", sa.Text()),
        sa.Column("achievement", sa.Text()),
        sa.Column("sort_order", sa.Integer()),
        *timestamps(),
    )
    op.create_table(
        "skill",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("level", sa.Integer()),
        sa.Column("description", sa.Text()),
        sa.Column("sort_order", sa.Integer()),
        *timestamps(),
    )
    op.create_table(
        "archive",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("content", sa.Text()),
        *timestamps(),
        sa.Column("tags", sa.String(400)),
        sa.Column("thumbnail", sa.String(400)),
        sa.Column("source_type", sa.String(80)),
        sa.Column("source_url", sa.String(400)),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommendation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_type", sa.String(40), nullable=False, server_default="archive"),
    )
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("author", sa.String(160)),
        sa.Column("publisher", sa.String(160)),
        sa.Column("genre", sa.String(120)),
        sa.Column("record_type", sa.String(80)),
        sa.Column("start_date", sa.String(40)),
        sa.Column("finish_date", sa.String(40)),
        sa.Column("status", sa.String(40)),
        sa.Column("cover_image", sa.String(400)),
        sa.Column("rating", sa.Float()),
        sa.Column("summary", sa.Text()),
        sa.Column("notion_url", sa.String(400), unique=True),
        sa.Column("notion_page_id", sa.String(160), unique=True),
        *timestamps(),
    )
    op.create_table(
        "reading_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), nullable=False),
        sa.Column("title", sa.String(240)),
        sa.Column("chapter", sa.String(160)),
        sa.Column("page", sa.String(80)),
        sa.Column("quote", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("my_thought", sa.Text()),
        sa.Column("question", sa.Text()),
        sa.Column("answer", sa.Text()),
        sa.Column("application", sa.Text()),
        sa.Column("keywords", sa.String(400)),
        sa.Column("source_url", sa.String(400)),
        *timestamps(),
    )
    op.create_table(
        "record_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("record_id", sa.Integer(), sa.ForeignKey("archive.id"), nullable=False),
        sa.Column("author", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        *timestamps(),
    )


def downgrade():
    for table in ("record_comments", "reading_notes", "books", "archive", "skill", "experience", "project", "profile"):
        op.drop_table(table)
