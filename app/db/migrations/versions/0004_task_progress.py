"""Explicit member-reported task progress."""
from alembic import op
import sqlalchemy as sa

revision = "0004_task_progress"
down_revision = "0003_approval_workflow"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("action_items", sa.Column("progress_percent", sa.Integer(), nullable=True))
    op.add_column("action_items", sa.Column("progress_updated_at", sa.DateTime(), nullable=True))
    op.add_column("action_items", sa.Column("progress_content", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("action_items", "progress_content")
    op.drop_column("action_items", "progress_updated_at")
    op.drop_column("action_items", "progress_percent")
