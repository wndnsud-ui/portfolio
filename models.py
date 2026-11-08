from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
from sqlalchemy import MetaData, or_

# 제약조건 이름 규칙: 마이그레이션이 SQLite·PostgreSQL 모두에서 같은 이름을 쓰게 한다
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING))


def utcnow():
    return datetime.utcnow()


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)


class PublishMixin:
    """공개 상태: draft(임시저장) / published(공개). published_at이 미래면 공개 예약."""

    status = db.Column(db.String(20), nullable=False, default="draft", server_default="published")
    published_at = db.Column(db.DateTime)

    @classmethod
    def visible(cls):
        return cls.query.filter(
            cls.status == "published",
            or_(cls.published_at.is_(None), cls.published_at <= utcnow()),
        )

    @property
    def is_visible(self):
        return self.status == "published" and (self.published_at is None or self.published_at <= utcnow())

    @property
    def is_scheduled(self):
        return self.status == "published" and self.published_at is not None and self.published_at > utcnow()

    @property
    def display_date(self):
        return self.published_at or self.created_at


class Profile(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default="최혜영")
    headline = db.Column(db.String(240), nullable=False, default="I turn problems into structure.")
    intro = db.Column(db.Text, default="문제를 발견하고, 구조를 만들고, 결과까지 연결합니다.")
    email = db.Column(db.String(160), default="")
    github = db.Column(db.String(240), default="")
    notion = db.Column(db.String(240), default="")
    photo = db.Column(db.String(400))
    resume_url = db.Column(db.String(400))
    # 소개 페이지 본문(블록)과 디자인, 홈 요약 카드 4장 [{label, value, note}]
    blocks = db.Column(db.JSON)
    design = db.Column(db.JSON)
    stats = db.Column(db.JSON)
    # 그 밖의 소개 문구: tagline(직무 한 줄), home_lead(홈 소개 문장), summary(이력서 한 줄 소개),
    # strengths(잘하는 것 4가지 [{title, text}]), seeking(새로운 일을 찾는 중 배지)
    extra = db.Column(db.JSON)

    def get(self, key, default=""):
        return (self.extra or {}).get(key) or default


class Page(TimestampMixin, db.Model):
    """한 장짜리 페이지(예: 모모슬 채널 소개). 주소(slug)마다 하나."""
    __tablename__ = "pages"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), nullable=False, unique=True)
    title = db.Column(db.String(160), nullable=False, default="")
    summary = db.Column(db.String(400))
    cover_image = db.Column(db.String(400))
    blocks = db.Column(db.JSON)
    design = db.Column(db.JSON)
    links = db.Column(db.JSON)  # {"youtube": url, "instagram": url, ...}
    is_public = db.Column(db.Boolean, nullable=False, default=False, server_default=sa.false())


class Project(PublishMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(200), unique=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    category = db.Column(db.String(80))  # 분류 칩 (예: 추천 · 데이터). 색은 design.accent
    subtitle = db.Column(db.String(240))
    description = db.Column(db.Text)
    period = db.Column(db.String(80))
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
    cover_image = db.Column(db.String(400))
    demo_url = db.Column(db.String(240), default="")
    github_url = db.Column(db.String(240), default="")
    notion_url = db.Column(db.String(240), default="")
    blocks = db.Column(db.JSON)
    design = db.Column(db.JSON)
    view_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")

    @property
    def tech_list(self):
        return [t.strip() for t in (self.tech_stack or "").replace("·", "/").replace(",", "/").split("/") if t.strip()]

    @property
    def image(self):
        return self.cover_image or self.thumbnail


class Experience(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(160), nullable=False)
    position = db.Column(db.String(160))
    start_date = db.Column(db.String(40))
    end_date = db.Column(db.String(40))
    description = db.Column(db.Text)
    achievement = db.Column(db.Text)
    kind = db.Column(db.String(20), nullable=False, default="work", server_default="work")  # work(경력) / edu(교육)
    sort_order = db.Column(db.Integer, default=0)

    @property
    def period(self):
        if self.start_date and self.end_date:
            return f"{self.start_date} – {self.end_date}"
        return self.start_date or self.end_date or ""


class Skill(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    level = db.Column(db.Integer, default=80)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)


class Archive(PublishMixin, TimestampMixin, db.Model):
    """글 하나. content_type: notes / life / reading"""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True)
    category = db.Column(db.String(80), nullable=False)
    summary = db.Column(db.Text)
    content = db.Column(db.Text)  # 예전 마크다운 본문(보존용). 화면은 blocks로 그린다.
    content_type = db.Column(db.String(40), default="notes", nullable=False)
    tags = db.Column(db.String(400))
    thumbnail = db.Column(db.String(400))
    cover_image = db.Column(db.String(400))
    blocks = db.Column(db.JSON)
    design = db.Column(db.JSON)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"))
    source_type = db.Column(db.String(80))
    source_url = db.Column(db.String(400))
    notion_last_edited_at = db.Column(db.DateTime)
    synced_at = db.Column(db.DateTime)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    view_count = db.Column(db.Integer, default=0, nullable=False)
    like_count = db.Column(db.Integer, default=0, nullable=False)
    recommendation_count = db.Column(db.Integer, default=0, nullable=False)
    comments = db.relationship("RecordComment", backref="record", cascade="all, delete-orphan", lazy=True)
    book = db.relationship("Book", backref=db.backref("posts", lazy=True))

    @property
    def tag_list(self):
        return [t.strip().lstrip("#") for t in (self.tags or "").split(",") if t.strip()]

    @property
    def image(self):
        return self.cover_image or self.thumbnail

    @property
    def visible_comments(self):
        return [c for c in self.comments if not c.is_hidden]


class RecordComment(TimestampMixin, db.Model):
    __tablename__ = "record_comments"
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey("archive.id"), nullable=False)
    author = db.Column(db.String(100), nullable=False, default="Anonymous")
    content = db.Column(db.Text, nullable=False)
    is_hidden = db.Column(db.Boolean, nullable=False, default=False, server_default=sa.false())


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
    notion_last_edited_at = db.Column(db.DateTime)
    synced_at = db.Column(db.DateTime)
    notes = db.relationship("ReadingNote", backref="book", cascade="all, delete-orphan", lazy=True)

    @property
    def period(self):
        if self.start_date and self.finish_date:
            return f"{self.start_date} – {self.finish_date}"
        return self.start_date or self.finish_date or ""


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


class Showcase(TimestampMixin, db.Model):
    """직접 운영하는 곳(모모슬의 휴식도감 /rest, 모두의 소파 /sofa)."""

    __tablename__ = "showcases"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), nullable=False, unique=True)
    title = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="soon", server_default="soon")  # live(운영 중) / soon(준비 중)
    intro = db.Column(db.Text)
    site_url = db.Column(db.String(400))
    channel_url = db.Column(db.String(400))
    tint = db.Column(db.String(20), nullable=False, default="mint", server_default="mint")
    cards = db.Column(db.JSON)   # 안내 카드 3장 [{title, text}]
    extra = db.Column(db.JSON)   # {label, summary, items:[{name}](도감 카드), hosts:[{name, bio}](진행자), contact}
    launch_date = db.Column(db.String(40))
    sort_order = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    videos = db.relationship("Video", backref="showcase", cascade="all, delete-orphan", lazy=True,
                             order_by="Video.sort_order")

    @property
    def is_live(self):
        return self.status == "live"

    @property
    def status_label(self):
        return "운영 중" if self.is_live else "준비 중"

    def get(self, key, default=""):
        return (self.extra or {}).get(key) or default

    @property
    def visible_videos(self):
        return [v for v in self.videos if v.is_visible]


class Video(TimestampMixin, db.Model):
    __tablename__ = "videos"
    id = db.Column(db.Integer, primary_key=True)
    showcase_id = db.Column(db.Integer, db.ForeignKey("showcases.id"), nullable=False)
    youtube_id = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False, default="")
    episode_no = db.Column(db.Integer)
    published_at = db.Column(db.String(40))  # 표시용 날짜 (예: 2026.11.07)
    duration = db.Column(db.String(20))      # 예: 12:34
    sort_order = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    is_visible = db.Column(db.Boolean, nullable=False, default=True, server_default=sa.true())

    @property
    def watch_url(self):
        return f"https://www.youtube.com/watch?v={self.youtube_id}"

    @property
    def thumbnail(self):
        return f"https://i.ytimg.com/vi/{self.youtube_id}/hqdefault.jpg"


class SyncLog(db.Model):
    """노션·파일 가져오기 실행 기록."""

    __tablename__ = "sync_logs"
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(40), nullable=False, default="notion")
    started_at = db.Column(db.DateTime, default=utcnow)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="running")
    created_count = db.Column(db.Integer, default=0)
    updated_count = db.Column(db.Integer, default=0)
    message = db.Column(db.Text)
