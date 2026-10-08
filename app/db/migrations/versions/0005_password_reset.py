"""Single-use password reset links and session revocation."""
from alembic import op
import sqlalchemy as sa
revision = "0005_password_reset"
down_revision = "0004_task_progress"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("password_resets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True))
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])

def downgrade():
    op.drop_table("password_resets")
    op.drop_column("users", "auth_version")
