"""Public member codes and email-less link invites for users without email (Kakao)."""
import secrets

from alembic import op
import sqlalchemy as sa

revision = "0008_member_codes"
down_revision = "0007_merge_auth_legacy"
branch_labels = None
depends_on = None

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def upgrade():
    connection = op.get_bind()
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("member_code", sa.String(length=16), nullable=True))
    users = sa.table("users", sa.column("id", sa.Integer), sa.column("member_code", sa.String))
    used = set()
    for (user_id,) in connection.execute(sa.select(users.c.id)).all():
        code = ""
        while not code or code in used:
            code = "".join(secrets.choice(ALPHABET) for _ in range(8))
        used.add(code)
        connection.execute(users.update().where(users.c.id == user_id).values(member_code=code))
    op.create_index("ix_users_member_code", "users", ["member_code"], unique=True)
    with op.batch_alter_table("workspace_invites") as batch:
        batch.alter_column("email", existing_type=sa.String(length=320), nullable=True)


def downgrade():
    op.execute("DELETE FROM workspace_invites WHERE email IS NULL")
    with op.batch_alter_table("workspace_invites") as batch:
        batch.alter_column("email", existing_type=sa.String(length=320), nullable=False)
    op.drop_index("ix_users_member_code", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("member_code")
