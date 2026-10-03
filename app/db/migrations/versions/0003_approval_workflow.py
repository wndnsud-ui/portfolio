"""Meeting review, task collaboration and approval workflow."""
from alembic import op
import sqlalchemy as sa
revision = "0003_approval_workflow"
down_revision = "0002_workspace_membership"
branch_labels = None
depends_on = None

def upgrade():
    connection = op.get_bind()
    tables = set(sa.inspect(connection).get_table_names())
    if 'notifications' not in tables:
        op.create_table('notifications',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('type', sa.String(length=60), primary_key=False, nullable=False),
            sa.Column('title', sa.String(length=250), primary_key=False, nullable=False),
            sa.Column('message', sa.Text(), primary_key=False, nullable=False),
            sa.Column('target_type', sa.String(length=20), primary_key=False, nullable=False),
            sa.Column('target_id', sa.Integer(), primary_key=False, nullable=False),
            sa.Column('is_read', sa.Boolean(), primary_key=False, nullable=False),
            sa.Column('dedup_key', sa.String(length=200), primary_key=False, nullable=True),
            sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
            sa.UniqueConstraint('dedup_key'),
        )
        op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)
    if 'workspace_invites' not in tables:
        op.create_table('workspace_invites',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('email', sa.String(length=320), primary_key=False, nullable=False),
            sa.Column('role', sa.String(length=20), primary_key=False, nullable=False),
            sa.Column('token_hash', sa.String(length=64), primary_key=False, nullable=False),
            sa.Column('expires_at', sa.DateTime(), primary_key=False, nullable=False),
            sa.Column('accepted_at', sa.DateTime(), primary_key=False, nullable=True),
            sa.UniqueConstraint('token_hash'),
        )
        op.create_index('ix_workspace_invites_workspace_id', 'workspace_invites', ['workspace_id'], unique=False)
    if 'activity_logs' not in tables:
        op.create_table('activity_logs',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id', ondelete=None), primary_key=False, nullable=False),
            sa.Column('event', sa.String(length=60), primary_key=False, nullable=False),
            sa.Column('target_type', sa.String(length=20), primary_key=False, nullable=False),
            sa.Column('target_id', sa.Integer(), primary_key=False, nullable=False),
            sa.Column('content', sa.Text(), primary_key=False, nullable=False),
            sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        )
        op.create_index('ix_activity_logs_project_id', 'activity_logs', ['project_id'], unique=False)
    if 'meeting_reviews' not in tables:
        op.create_table('meeting_reviews',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id', ondelete=None), primary_key=False, nullable=False),
            sa.Column('action', sa.String(length=40), primary_key=False, nullable=False),
            sa.Column('previous_status', sa.String(length=30), primary_key=False, nullable=False),
            sa.Column('new_status', sa.String(length=30), primary_key=False, nullable=False),
            sa.Column('content', sa.Text(), primary_key=False, nullable=False),
            sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        )
        op.create_index('ix_meeting_reviews_meeting_id', 'meeting_reviews', ['meeting_id'], unique=False)
    if 'transcription_jobs' not in tables:
        op.create_table('transcription_jobs',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete=None), primary_key=False, nullable=False),
            sa.Column('status', sa.String(length=30), primary_key=False, nullable=False),
            sa.Column('progress', sa.Integer(), primary_key=False, nullable=False),
            sa.Column('error', sa.Text(), primary_key=False, nullable=True),
            sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        )
        op.create_index('ix_transcription_jobs_meeting_id', 'transcription_jobs', ['meeting_id'], unique=False)
    if 'final_results' not in tables:
        op.create_table('final_results',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('task_id', sa.Integer(), sa.ForeignKey('action_items.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id', ondelete=None), primary_key=False, nullable=False),
            sa.Column('title', sa.Text(), primary_key=False, nullable=False),
            sa.Column('content', sa.Text(), primary_key=False, nullable=False),
            sa.Column('assignee_id', sa.Integer(), sa.ForeignKey('users.id', ondelete=None), primary_key=False, nullable=True),
            sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
            sa.UniqueConstraint('task_id'),
        )
        op.create_index('ix_final_results_project_id', 'final_results', ['project_id'], unique=False)
    if 'task_attachments' not in tables:
        op.create_table('task_attachments',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('task_id', sa.Integer(), sa.ForeignKey('action_items.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('uploaded_by', sa.Integer(), sa.ForeignKey('users.id', ondelete=None), primary_key=False, nullable=False),
            sa.Column('file_name', sa.String(length=255), primary_key=False, nullable=False),
            sa.Column('storage_key', sa.String(length=80), primary_key=False, nullable=False),
            sa.Column('file_type', sa.String(length=20), primary_key=False, nullable=False),
            sa.Column('size', sa.Integer(), primary_key=False, nullable=False),
            sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
            sa.UniqueConstraint('storage_key'),
        )
        op.create_index('ix_task_attachments_task_id', 'task_attachments', ['task_id'], unique=False)
    if 'task_comments' not in tables:
        op.create_table('task_comments',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('task_id', sa.Integer(), sa.ForeignKey('action_items.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete=None), primary_key=False, nullable=False),
            sa.Column('content', sa.Text(), primary_key=False, nullable=False),
            sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
            sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
            sa.Column('deleted_at', sa.DateTime(), primary_key=False, nullable=True),
        )
        op.create_index('ix_task_comments_task_id', 'task_comments', ['task_id'], unique=False)
    if 'task_progress' not in tables:
        op.create_table('task_progress',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('task_id', sa.Integer(), sa.ForeignKey('action_items.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete=None), primary_key=False, nullable=False),
            sa.Column('content', sa.Text(), primary_key=False, nullable=False),
            sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
            sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
        )
        op.create_index('ix_task_progress_task_id', 'task_progress', ['task_id'], unique=False)
    if 'task_reviews' not in tables:
        op.create_table('task_reviews',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('task_id', sa.Integer(), sa.ForeignKey('action_items.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id', ondelete=None), primary_key=False, nullable=False),
            sa.Column('action', sa.String(length=40), primary_key=False, nullable=False),
            sa.Column('previous_status', sa.String(length=30), primary_key=False, nullable=False),
            sa.Column('new_status', sa.String(length=30), primary_key=False, nullable=False),
            sa.Column('content', sa.Text(), primary_key=False, nullable=False),
            sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        )
        op.create_index('ix_task_reviews_task_id', 'task_reviews', ['task_id'], unique=False)
    if 'transcript_chunks' not in tables:
        op.create_table('transcript_chunks',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('job_id', sa.Integer(), sa.ForeignKey('transcription_jobs.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('sequence', sa.Integer(), primary_key=False, nullable=False),
            sa.Column('content', sa.Text(), primary_key=False, nullable=False),
            sa.UniqueConstraint('job_id', 'sequence'),
        )
        op.create_index('ix_transcript_chunks_job_id', 'transcript_chunks', ['job_id'], unique=False)
    if 'comment_mentions' not in tables:
        op.create_table('comment_mentions',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('comment_id', sa.Integer(), sa.ForeignKey('task_comments.id', ondelete='CASCADE'), primary_key=False, nullable=False),
            sa.Column('mentioned_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete=None), primary_key=False, nullable=False),
            sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
            sa.UniqueConstraint('comment_id', 'mentioned_user_id'),
        )
    columns = {c["name"] for c in sa.inspect(connection).get_columns('meetings')}
    with op.batch_alter_table('meetings') as batch:
        if 'recorder_id' not in columns:
            batch.add_column(sa.Column('recorder_id', sa.Integer(), nullable=True, server_default=None))
            batch.create_foreign_key("fk_meetings_recorder_id", 'users', ['recorder_id'], ["id"])
        if 'report_status' not in columns:
            batch.add_column(sa.Column('report_status', sa.String(30), nullable=False, server_default='DRAFT'))
            batch.create_index("ix_meetings_report_status", ['report_status'])
        if 'input_type' not in columns:
            batch.add_column(sa.Column('input_type', sa.String(20), nullable=False, server_default='text_paste'))
        if 'candidates' not in columns:
            batch.add_column(sa.Column('candidates', sa.JSON(), nullable=False, server_default='{}'))
    columns = {c["name"] for c in sa.inspect(connection).get_columns('action_items')}
    with op.batch_alter_table('action_items') as batch:
        if 'assignee_id' not in columns:
            batch.add_column(sa.Column('assignee_id', sa.Integer(), nullable=True, server_default=None))
            batch.create_foreign_key("fk_action_items_assignee_id", 'users', ['assignee_id'], ["id"])
            batch.create_index("ix_action_items_assignee_id", ['assignee_id'])
        if 'assigned_by' not in columns:
            batch.add_column(sa.Column('assigned_by', sa.Integer(), nullable=True, server_default=None))
            batch.create_foreign_key("fk_action_items_assigned_by", 'users', ['assigned_by'], ["id"])
        if 'description' not in columns:
            batch.add_column(sa.Column('description', sa.Text(), nullable=True, server_default=None))
        if 'workflow_status' not in columns:
            batch.add_column(sa.Column('workflow_status', sa.String(30), nullable=True, server_default=None))
            batch.create_index("ix_action_items_workflow_status", ['workflow_status'])

def downgrade():
    raise RuntimeError("Approval history cannot be automatically deleted. Restore a reviewed backup instead.")
