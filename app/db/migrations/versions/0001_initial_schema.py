"""Frozen initial DecisionFlow schema."""
from alembic import op
import sqlalchemy as sa
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

def initial_metadata():
    metadata = sa.MetaData()
    sa.Table('notion_connections', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('workspace_name', sa.String(length=200), primary_key=False, nullable=True),
        sa.Column('meeting_database_id', sa.String(length=120), primary_key=False, nullable=True),
        sa.Column('action_item_database_id', sa.String(length=120), primary_key=False, nullable=True),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Table('users', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('email', sa.String(length=320), primary_key=False, nullable=False),
        sa.Column('nickname', sa.String(length=120), primary_key=False, nullable=True),
        sa.Column('password_hash', sa.String(length=255), primary_key=False, nullable=True),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Index('ix_users_email', metadata.tables['users'].c['email'], unique=True)
    sa.Index('ix_users_id', metadata.tables['users'].c['id'], unique=False)
    sa.Table('auth_accounts', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('provider', sa.String(length=40), primary_key=False, nullable=False),
        sa.Column('provider_account_id', sa.String(length=255), primary_key=False, nullable=False),
        sa.Column('provider_email', sa.String(length=320), primary_key=False, nullable=True),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.UniqueConstraint('provider', 'provider_account_id', name='uq_auth_provider_account'),
    )
    sa.Index('ix_auth_accounts_provider', metadata.tables['auth_accounts'].c['provider'], unique=False)
    sa.Index('ix_auth_accounts_user_id', metadata.tables['auth_accounts'].c['user_id'], unique=False)
    sa.Table('blog_posts', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('title', sa.String(length=250), primary_key=False, nullable=False),
        sa.Column('slug', sa.String(length=280), primary_key=False, nullable=False),
        sa.Column('summary', sa.Text(), primary_key=False, nullable=True),
        sa.Column('content', sa.Text(), primary_key=False, nullable=False),
        sa.Column('category', sa.String(length=120), primary_key=False, nullable=True),
        sa.Column('tags', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('thumbnail_url', sa.String(length=500), primary_key=False, nullable=True),
        sa.Column('status', sa.String(length=20), primary_key=False, nullable=False),
        sa.Column('source_type', sa.String(length=40), primary_key=False, nullable=False),
        sa.Column('source_id', sa.Integer(), primary_key=False, nullable=True),
        sa.Column('published_at', sa.DateTime(), primary_key=False, nullable=True),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Index('ix_blog_posts_category', metadata.tables['blog_posts'].c['category'], unique=False)
    sa.Index('ix_blog_posts_slug', metadata.tables['blog_posts'].c['slug'], unique=True)
    sa.Index('ix_blog_posts_source_id', metadata.tables['blog_posts'].c['source_id'], unique=False)
    sa.Index('ix_blog_posts_id', metadata.tables['blog_posts'].c['id'], unique=False)
    sa.Index('ix_blog_posts_user_id', metadata.tables['blog_posts'].c['user_id'], unique=False)
    sa.Index('ix_blog_posts_status', metadata.tables['blog_posts'].c['status'], unique=False)
    sa.Table('user_settings', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('openai_api_key_encrypted', sa.Text(), primary_key=False, nullable=True),
        sa.Column('notion_api_key_encrypted', sa.Text(), primary_key=False, nullable=True),
        sa.Column('notion_database_id', sa.String(length=255), primary_key=False, nullable=True),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Index('ix_user_settings_user_id', metadata.tables['user_settings'].c['user_id'], unique=True)
    sa.Table('projects', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=False, nullable=True),
        sa.Column('name', sa.String(length=200), primary_key=False, nullable=False),
        sa.Column('description', sa.Text(), primary_key=False, nullable=True),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Index('ix_projects_name', metadata.tables['projects'].c['name'], unique=False)
    sa.Index('ix_projects_user_id', metadata.tables['projects'].c['user_id'], unique=False)
    sa.Index('ix_projects_id', metadata.tables['projects'].c['id'], unique=False)
    sa.Table('meetings', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=False, nullable=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('title', sa.String(length=250), primary_key=False, nullable=False),
        sa.Column('meeting_date', sa.Date(), primary_key=False, nullable=False),
        sa.Column('participants', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('speaker_names', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('summary', sa.Text(), primary_key=False, nullable=True),
        sa.Column('discussion', sa.Text(), primary_key=False, nullable=True),
        sa.Column('undecided_topics', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('analysis_status', sa.String(length=20), primary_key=False, nullable=False),
        sa.Column('notion_sync_status', sa.String(length=20), primary_key=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Index('ix_meetings_project_id', metadata.tables['meetings'].c['project_id'], unique=False)
    sa.Index('ix_meetings_user_id', metadata.tables['meetings'].c['user_id'], unique=False)
    sa.Index('ix_meetings_id', metadata.tables['meetings'].c['id'], unique=False)
    sa.Index('ix_meetings_title', metadata.tables['meetings'].c['title'], unique=False)
    sa.Table('action_items', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=False, nullable=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='SET NULL'), primary_key=False, nullable=True),
        sa.Column('task', sa.Text(), primary_key=False, nullable=False),
        sa.Column('assignee', sa.String(length=120), primary_key=False, nullable=True),
        sa.Column('due_date', sa.Date(), primary_key=False, nullable=True),
        sa.Column('status', sa.String(length=20), primary_key=False, nullable=False),
        sa.Column('priority', sa.String(length=20), primary_key=False, nullable=False),
        sa.Column('risk_score', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('risk_level', sa.String(length=20), primary_key=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('status_changed_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('completed_at', sa.DateTime(), primary_key=False, nullable=True),
    )
    sa.Index('ix_action_items_assignee', metadata.tables['action_items'].c['assignee'], unique=False)
    sa.Index('ix_action_items_risk_level', metadata.tables['action_items'].c['risk_level'], unique=False)
    sa.Index('ix_action_items_project_id', metadata.tables['action_items'].c['project_id'], unique=False)
    sa.Index('ix_action_items_status', metadata.tables['action_items'].c['status'], unique=False)
    sa.Index('ix_action_items_meeting_id', metadata.tables['action_items'].c['meeting_id'], unique=False)
    sa.Index('ix_action_items_user_id', metadata.tables['action_items'].c['user_id'], unique=False)
    sa.Index('ix_action_items_id', metadata.tables['action_items'].c['id'], unique=False)
    sa.Index('ix_action_items_due_date', metadata.tables['action_items'].c['due_date'], unique=False)
    sa.Table('decisions', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=False, nullable=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='SET NULL'), primary_key=False, nullable=True),
        sa.Column('topic', sa.String(length=250), primary_key=False, nullable=False),
        sa.Column('value', sa.Text(), primary_key=False, nullable=False),
        sa.Column('status', sa.String(length=20), primary_key=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Index('ix_decisions_meeting_id', metadata.tables['decisions'].c['meeting_id'], unique=False)
    sa.Index('ix_decisions_id', metadata.tables['decisions'].c['id'], unique=False)
    sa.Index('ix_decisions_project_id', metadata.tables['decisions'].c['project_id'], unique=False)
    sa.Index('ix_decisions_user_id', metadata.tables['decisions'].c['user_id'], unique=False)
    sa.Index('ix_decisions_topic', metadata.tables['decisions'].c['topic'], unique=False)
    sa.Table('notion_sync_logs', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('status', sa.String(length=20), primary_key=False, nullable=False),
        sa.Column('notion_page_id', sa.String(length=120), primary_key=False, nullable=True),
        sa.Column('error_message', sa.Text(), primary_key=False, nullable=True),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Index('ix_notion_sync_logs_meeting_id', metadata.tables['notion_sync_logs'].c['meeting_id'], unique=False)
    sa.Table('transcripts', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('content', sa.Text(), primary_key=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Index('ix_transcripts_meeting_id', metadata.tables['transcripts'].c['meeting_id'], unique=True)
    sa.Table('action_item_predictions', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('action_item_id', sa.Integer(), sa.ForeignKey('action_items.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('delay_probability', sa.Float(), primary_key=False, nullable=False),
        sa.Column('risk_level', sa.String(length=20), primary_key=False, nullable=False),
        sa.Column('model_version', sa.String(length=50), primary_key=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Index('ix_action_item_predictions_action_item_id', metadata.tables['action_item_predictions'].c['action_item_id'], unique=False)
    sa.Table('decision_history', metadata,
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('decision_id', sa.Integer(), sa.ForeignKey('decisions.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='SET NULL'), primary_key=False, nullable=True),
        sa.Column('previous_value', sa.Text(), primary_key=False, nullable=True),
        sa.Column('new_value', sa.Text(), primary_key=False, nullable=False),
        sa.Column('changed_at', sa.DateTime(), primary_key=False, nullable=False),
    )
    sa.Index('ix_decision_history_decision_id', metadata.tables['decision_history'].c['decision_id'], unique=False)
    return metadata

def upgrade():
    initial_metadata().create_all(bind=op.get_bind(), checkfirst=True)

def downgrade():
    raise RuntimeError("Automatic initial-schema deletion is disabled; restore a reviewed backup instead.")
