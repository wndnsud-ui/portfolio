"""Merge the deployed legacy repair and authentication migration histories."""
revision = "0007_merge_auth_legacy"
down_revision = ("0006_example_projects", "0005_legacy_columns")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
