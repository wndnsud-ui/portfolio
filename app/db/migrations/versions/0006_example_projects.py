"""Identify onboarding example projects without relying on their names."""
from alembic import op
import sqlalchemy as sa
revision = "0006_example_projects"
down_revision = "0005_password_reset"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("projects", sa.Column("is_example", sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column("projects", "is_example")
