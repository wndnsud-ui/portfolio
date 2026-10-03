"""Add workspace membership and preserve existing project ownership."""
from alembic import op
import sqlalchemy as sa

revision = "0002_workspace_membership"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    if "workspaces" not in tables:
        op.create_table("workspaces", sa.Column("id", sa.Integer(), primary_key=True),
                        sa.Column("name", sa.String(200), nullable=False),
                        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
                        sa.Column("created_at", sa.DateTime(), nullable=False))
    if "workspace_members" not in tables:
        op.create_table("workspace_members", sa.Column("id", sa.Integer(), primary_key=True),
                        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
                        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                        sa.Column("role", sa.String(20), nullable=False), sa.UniqueConstraint("workspace_id", "user_id"))
        op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
        op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])
    if "workspace_id" not in {c["name"] for c in inspector.get_columns("projects")}:
        with op.batch_alter_table("projects") as batch:
            batch.add_column(sa.Column("workspace_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_projects_workspace", "workspaces", ["workspace_id"], ["id"])
            batch.create_index("ix_projects_workspace_id", ["workspace_id"])
    if "project_members" not in tables:
        op.create_table("project_members", sa.Column("id", sa.Integer(), primary_key=True),
                        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
                        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                        sa.UniqueConstraint("project_id", "user_id"))
        op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
        op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
    metadata = sa.MetaData()
    metadata.reflect(bind=connection, only=["users", "projects", "workspaces", "workspace_members", "project_members"])
    users, projects, workspaces, members, project_members = [metadata.tables[n] for n in ["users", "projects", "workspaces", "workspace_members", "project_members"]]
    from datetime import datetime
    for user in connection.execute(sa.select(users)).mappings().all():
        legacy = connection.execute(sa.select(projects.c.id).where(projects.c.user_id == user["id"], projects.c.workspace_id.is_(None))).scalars().all()
        if not legacy:
            continue
        wid = connection.execute(workspaces.insert().values(name=f"{user['nickname'] or user['email']} Workspace", created_by=user["id"], created_at=datetime.utcnow()).returning(workspaces.c.id)).scalar_one()
        connection.execute(members.insert().values(workspace_id=wid, user_id=user["id"], role="OWNER"))
        connection.execute(projects.update().where(projects.c.id.in_(legacy)).values(workspace_id=wid))
        for pid in legacy:
            connection.execute(project_members.insert().values(project_id=pid, user_id=user["id"]))


def downgrade():
    raise RuntimeError("Workspace membership migration requires a reviewed backup restoration; automatic destructive downgrade is disabled.")
