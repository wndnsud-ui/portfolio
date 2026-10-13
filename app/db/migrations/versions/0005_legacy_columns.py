"""Repair columns missing from legacy databases without replacing existing data."""
from alembic import op
import sqlalchemy as sa

revision = "0005_legacy_columns"
down_revision = "0004_task_progress"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    for table in ("projects", "meetings", "action_items", "decisions"):
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "user_id" not in columns:
            op.add_column(table, sa.Column("user_id", sa.Integer(), nullable=True))
    columns = {column["name"] for column in inspector.get_columns("meetings")}
    if "speaker_names" not in columns:
        op.add_column("meetings", sa.Column("speaker_names", sa.JSON(), server_default=sa.text("'{}'"), nullable=True))


def downgrade():
    # These columns may predate this revision and contain existing user data.
    pass
