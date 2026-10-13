"""Meeting attachments for photos of whiteboards and paper minutes."""
from alembic import op
import sqlalchemy as sa

revision = "0009_meeting_attachments"
down_revision = "0008_member_codes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("meeting_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_meeting_attachments_meeting_id", "meeting_attachments", ["meeting_id"], unique=False)


def downgrade():
    op.drop_index("ix_meeting_attachments_meeting_id", table_name="meeting_attachments")
    op.drop_table("meeting_attachments")
