from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Profile(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default="최혜영")
    headline = db.Column(db.String(240), nullable=False, default="I turn problems into structure.")
    intro = db.Column(db.Text, default="문제를 발견하고, 구조를 만들고, 결과까지 연결합니다.")
    email = db.Column(db.String(160), default="hello@example.com")
    github = db.Column(db.String(240), default="#")
    notion = db.Column(db.String(240), default="#")

class Project(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    subtitle = db.Column(db.String(240))
    description = db.Column(db.Text)
    problem = db.Column(db.Text)
    role = db.Column(db.Text)
    process = db.Column(db.Text)
    action = db.Column(db.Text)
    trouble = db.Column(db.Text)
    solution = db.Column(db.Text)
    result = db.Column(db.Text)
    insight = db.Column(db.Text)
    tech_stack = db.Column(db.String(400))
    thumbnail = db.Column(db.String(240))
    github_url = db.Column(db.String(240), default="#")
    notion_url = db.Column(db.String(240), default="#")

class Experience(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(160), nullable=False)
    position = db.Column(db.String(160))
    start_date = db.Column(db.String(40))
    end_date = db.Column(db.String(40))
    description = db.Column(db.Text)
    achievement = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)

class Skill(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    level = db.Column(db.Integer, default=80)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)

class Archive(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    summary = db.Column(db.Text)
    content = db.Column(db.Text)
    tags = db.Column(db.String(400))
    thumbnail = db.Column(db.String(400))
    source_type = db.Column(db.String(80))
    source_url = db.Column(db.String(400))
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    view_count = db.Column(db.Integer, default=0, nullable=False)
    like_count = db.Column(db.Integer, default=0, nullable=False)
    recommendation_count = db.Column(db.Integer, default=0, nullable=False)
    comments = db.relationship("RecordComment", backref="record", cascade="all, delete-orphan", lazy=True)

class RecordComment(TimestampMixin, db.Model):
    __tablename__ = "record_comments"
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey("archive.id"), nullable=False)
    author = db.Column(db.String(100), nullable=False, default="Anonymous")
    content = db.Column(db.Text, nullable=False)

class Book(TimestampMixin, db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(240), nullable=False)
    author = db.Column(db.String(160))
    publisher = db.Column(db.String(160))
    genre = db.Column(db.String(120))
    record_type = db.Column(db.String(80))
    start_date = db.Column(db.String(40))
    finish_date = db.Column(db.String(40))
    status = db.Column(db.String(40), default="reading")
    cover_image = db.Column(db.String(400))
    rating = db.Column(db.Float)
    summary = db.Column(db.Text)
    notion_url = db.Column(db.String(400), unique=True)
    notion_page_id = db.Column(db.String(160), unique=True)
    notes = db.relationship("ReadingNote", backref="book", cascade="all, delete-orphan", lazy=True)

class ReadingNote(TimestampMixin, db.Model):
    __tablename__ = "reading_notes"
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    title = db.Column(db.String(240))
    chapter = db.Column(db.String(160))
    page = db.Column(db.String(80))
    quote = db.Column(db.Text)
    summary = db.Column(db.Text)
    my_thought = db.Column(db.Text)
    question = db.Column(db.Text)
    answer = db.Column(db.Text)
    application = db.Column(db.Text)
    keywords = db.Column(db.String(400))
    source_url = db.Column(db.String(400))
