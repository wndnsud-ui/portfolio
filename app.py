import os
from datetime import datetime
from email.utils import format_datetime

import click
from flask import Flask, Response, abort, flash, redirect, render_template, request, session, url_for
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import String, case, cast, func, or_
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash

from auth import is_admin
from config import Config
from content import (
    BLOCK_TYPES, BOOK_STATUS, BOOK_STATUS_TINT, CATEGORIES, DESIGN_OPTIONS, KINDS, NOTE_TYPES, SINGLE_KINDS, SKILL_GROUPS,
    TYPE_OF_KIND, design_classes, highlight, nl2br, normalize_design, plain, plain_excerpt, read_minutes, render_body, tint,
)
from models import Archive, Book, Experience, Profile, Project, ReadingNote, RecordComment, Showcase, Skill, db

app = Flask(__name__)
app.config.from_object(Config)
if os.environ.get("DATABASE_URL") and not os.environ.get("SECRET_KEY"):
    raise RuntimeError("운영 환경(DATABASE_URL 설정됨)에서는 SECRET_KEY 환경변수가 필요합니다.")
# Railway 등 앞단 프록시가 붙인 X-Forwarded-* 를 한 단계만 믿는다 (https 주소, 방문자 IP)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
db.init_app(app)
migrate = Migrate(app, db, render_as_batch=True)
csrf = CSRFProtect(app)

from admin import admin_bp  # noqa: E402  (admin이 app의 헬퍼를 쓰므로 뒤에서 등록)

app.register_blueprint(admin_bp)

from chatgpt_bridge import api as chatgpt_api  # noqa: E402

# These endpoints accept a dedicated Bearer key, not browser cookies.
csrf.exempt(chatgpt_api)
app.register_blueprint(chatgpt_api)

from mcp_auth import routes as mcp_oauth  # noqa: E402
from mcp_server import routes as reading_mcp  # noqa: E402

# OAuth token exchange and MCP authenticate independently of browser sessions.
# The owner consent and revocation forms stay under the CSRF-protected admin blueprint.
csrf.exempt(mcp_oauth)
csrf.exempt(reading_mcp)
app.register_blueprint(mcp_oauth)
app.register_blueprint(reading_mcp)

PAGE_SIZE = 12
COMMENT_LIMIT = 500


# ------------------------------------------------------------------ 템플릿 도우미
app.jinja_env.filters.update(nl2br=nl2br, design_classes=design_classes, excerpt=plain_excerpt, hl=highlight,
                             plain=plain, minutes=read_minutes)


@app.template_filter("date")
def format_date(value, fmt="%Y.%m.%d"):
    return value.strftime(fmt) if value else ""


def post_url(post, external=False):
    return url_for("notes_detail", key=post.slug or post.id, _external=external)


def project_url(project, external=False):
    return url_for("project_detail", key=project.slug or project.id, _external=external)


def post_label(post):
    """기록 카드의 분류 칩 글자: 독서 노트는 「독서」로 짧게."""
    return "독서" if post.content_type == "reading" else post.category


def post_tint(post):
    return tint(post.category, tint(post.content_type))


def project_tint(project):
    return normalize_design(project.design, "project")["accent"]


# 매크로(_components.html)에서도 쓰므로 요청과 무관한 도우미는 전역으로 등록한다
app.jinja_env.globals.update(
    post_url=post_url, project_url=project_url, post_label=post_label, post_tint=post_tint, project_tint=project_tint, tint=tint, KINDS=KINDS,
    SINGLE_KINDS=SINGLE_KINDS, DESIGN_OPTIONS=DESIGN_OPTIONS, BLOCK_TYPES=BLOCK_TYPES, CATEGORIES=CATEGORIES,
    NOTE_TYPES=NOTE_TYPES, TYPE_OF_KIND=TYPE_OF_KIND, SKILL_GROUPS=SKILL_GROUPS, BOOK_STATUS=BOOK_STATUS,
    BOOK_STATUS_TINT=BOOK_STATUS_TINT,
)


@app.context_processor
def template_globals():
    return {"profile": Profile.query.first(), "is_admin": is_admin(), "now": datetime.utcnow(),
            "showcases": Showcase.query.order_by(Showcase.sort_order, Showcase.id).all()}


# ------------------------------------------------------------------ 조회 도우미
def by_key(query, model, key):
    if str(key).isdigit():
        item = query.filter(model.id == int(key)).first()
        if item:
            return item
    return query.filter(model.slug == str(key)).first()


def date_order():
    return func.coalesce(Archive.published_at, Archive.created_at)


def search_filter(model, q):
    like = f"%{q}%"
    columns = [model.title, cast(model.blocks, String)]
    if model is Archive:
        columns += [Archive.summary, Archive.content, Archive.tags, Archive.category]
    else:
        columns += [Project.subtitle, Project.description, Project.problem, Project.result, Project.tech_stack]
    return or_(*[column.ilike(like) for column in columns])


def bump_views(item):
    if not is_admin():
        item.view_count = (item.view_count or 0) + 1
        db.session.commit()


DEFAULT_STATS = [
    {"label": "업무운영 경력", "value": "20년", "note": "감정평가법인 5곳"},
    {"label": "마지막 직책", "value": "팀장", "note": "㈜통일감정평가법인 차장"},
    {"label": "만든 서비스", "value": "3개", "note": "기획부터 구현까지"},
    {"label": "지금 배우는 것", "value": "AI Agent", "note": "Python · SQL · FastAPI"},
]
STAT_TINTS = ["butter", "mint", "sky", "pink"]


def home_stats(profile):
    stats = [s for s in ((profile.stats if profile else None) or []) if isinstance(s, dict) and s.get("value")]
    return (stats or DEFAULT_STATS)[:4]


def skill_groups():
    groups = {}
    for skill in Skill.query.order_by(Skill.sort_order, Skill.id).all():
        groups.setdefault(skill.category, []).append(skill)
    order = list(SKILL_GROUPS)
    return sorted(groups.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else len(order))


def experiences(kind=None):
    query = Experience.query.order_by(Experience.sort_order, Experience.id)
    return query.filter(Experience.kind == kind).all() if kind else query.all()


# ------------------------------------------------------------------ 홈
@app.route("/")
def home():
    profile = Profile.query.first()
    projects = Project.visible().order_by(Project.sort_order, Project.id).limit(3).all()
    recent = (Archive.visible().order_by(Archive.is_pinned.desc(), date_order().desc()).limit(12).all())
    reading = (Book.query.filter(Book.status == "reading").order_by(Book.updated_at.desc()).first()
               or Book.query.filter(Book.status == "completed").order_by(Book.updated_at.desc()).first())
    reading_post = None
    if reading:
        reading_post = (Archive.visible().filter(Archive.book_id == reading.id).order_by(date_order().desc()).first())
    return render_template("home.html", projects=projects, recent=recent, reading=reading, reading_post=reading_post,
                           stats=home_stats(profile), stat_tints=STAT_TINTS, timeline=experiences()[:3],
                           skills=skill_groups())


# ------------------------------------------------------------------ 프로젝트
@app.route("/projects")
def projects():
    items = Project.visible().order_by(Project.sort_order, Project.id).all()
    return render_template("projects/list.html", projects=items)


@app.route("/projects/<key>")
def project_detail(key):
    query = Project.query if is_admin() else Project.visible()
    project = by_key(query, Project, key) or abort(404)
    bump_views(project)
    body, toc, minutes = render_body(project.blocks)
    ordered = Project.visible().order_by(Project.sort_order, Project.id).all()
    index = next((i for i, p in enumerate(ordered) if p.id == project.id), None)
    next_item = None
    if index is not None and len(ordered) > 1:
        next_item = ordered[(index + 1) % len(ordered)]
    return render_template("projects/detail.html", project=project, body=body, toc=toc, minutes=minutes,
                           design=normalize_design(project.design, "project"), next_item=next_item)


@app.route("/portfolio")
def portfolio():
    """기획 포트폴리오 장문 페이지(14장 시안 기반)."""
    return render_template("pages/portfolio.html", projects=Project.visible().order_by(Project.sort_order, Project.id).all())


# ------------------------------------------------------------------ 기록 (공부·업무 / 독서 / 일상)
@app.route("/notes")
def notes():
    type_ = request.args.get("type", "")
    type_ = type_ if type_ in NOTE_TYPES else ""
    q = request.args.get("q", "").strip()[:80]
    sort = request.args.get("sort", "latest")
    page = request.args.get("page", 1, type=int)
    base = Archive.visible()
    counts = dict(base.with_entities(Archive.content_type, func.count(Archive.id)).group_by(Archive.content_type).all())
    query = base
    if type_:
        query = query.filter(Archive.content_type == NOTE_TYPES[type_][1])
    if q:
        query = query.filter(search_filter(Archive, q))
    if sort == "popular":
        query = query.order_by(Archive.view_count.desc(), Archive.like_count.desc(), date_order().desc())
    else:
        sort = "latest"
        query = query.order_by(Archive.is_pinned.desc(), date_order().desc())
    pagination = query.paginate(page=page, per_page=PAGE_SIZE, error_out=False)
    tabs = [("", "전체", sum(counts.values()), "")] + [
        (key, label, counts.get(kind, 0), tint(key)) for key, (label, kind) in NOTE_TYPES.items()]
    return render_template("posts/list.html", pagination=pagination, tabs=tabs, type=type_, q=q, sort=sort)


@app.route("/notes/<key>")
def notes_detail(key):
    query = Archive.query if is_admin() else Archive.visible()
    post = by_key(query, Archive, key) or abort(404)
    bump_views(post)
    body, toc, minutes = render_body(post.blocks)
    related = (Archive.visible().filter(Archive.id != post.id)
               .order_by((Archive.content_type == post.content_type).desc(), date_order().desc()).limit(3).all())
    liked = post.id in session.get("liked_records", [])
    return render_template("posts/detail.html", post=post, body=body, toc=toc, minutes=minutes,
                           design=normalize_design(post.design, post.content_type), related=related, liked=liked,
                           comment_limit=COMMENT_LIMIT)


@app.post("/posts/<int:post_id>/like")
def like_post(post_id):
    post = Archive.visible().filter(Archive.id == post_id).first_or_404()
    liked = set(session.get("liked_records", []))
    if post_id in liked:
        post.like_count = max(0, post.like_count - 1)
        liked.discard(post_id)
    else:
        post.like_count += 1
        liked.add(post_id)
    session["liked_records"] = sorted(liked)
    db.session.commit()
    return redirect(post_url(post) + "#reactions")


@app.post("/posts/<int:post_id>/comments")
def add_comment(post_id):
    post = Archive.visible().filter(Archive.id == post_id).first_or_404()
    if request.form.get("website"):  # 숨김 필드: 사람에게는 보이지 않으므로 값이 있으면 자동 입력으로 본다
        return redirect(post_url(post) + "#comments")
    author = (request.form.get("author", "").strip() or "익명")[:40]
    content = request.form.get("content", "").strip()
    if not content:
        flash("댓글 내용을 적어 주세요.", "error")
    elif len(content) > COMMENT_LIMIT:
        flash(f"댓글은 {COMMENT_LIMIT}자까지 쓸 수 있어요.", "error")
    else:
        db.session.add(RecordComment(record_id=post.id, author=author, content=content))
        db.session.commit()
        flash("댓글을 남겼어요. 고마워요!", "success")
    return redirect(post_url(post) + "#comments")


# ------------------------------------------------------------------ 독서
@app.route("/reading")
def reading():
    status = request.args.get("status", "")
    status = status if status in BOOK_STATUS else ""
    query = Book.query
    if status:
        query = query.filter(Book.status == status)
    order = case((Book.status == "reading", 0), (Book.status == "completed", 1), else_=2)
    books = query.order_by(order, Book.updated_at.desc()).all()
    note_rows = (Archive.visible().filter(Archive.content_type == "reading", Archive.book_id.isnot(None))
                 .with_entities(Archive.book_id, func.count(Archive.id), func.max(date_order()))
                 .group_by(Archive.book_id).all())
    notes_by_book = {book_id: (count, last) for book_id, count, last in note_rows}
    return render_template("reading/list.html", books=books, status=status, total=Book.query.count(),
                           note_total=Archive.visible().filter(Archive.content_type == "reading").count(),
                           notes_by_book=notes_by_book)


@app.route("/reading/books/<int:book_id>")
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    posts = (Archive.visible().filter(Archive.content_type == "reading", Archive.book_id == book.id)
             .order_by(date_order().desc()).all())
    legacy = ReadingNote.query.filter_by(book_id=book.id).order_by(ReadingNote.id).all()
    return render_template("reading/book.html", book=book, posts=posts, legacy=legacy)


# ------------------------------------------------------------------ 소개·이력서
@app.route("/about")
def about():
    profile = Profile.query.first()
    body, toc, minutes = render_body(profile.blocks if profile else [])
    return render_template("about.html", body=body, work=experiences("work"), education=experiences("edu"),
                           skills=skill_groups(), projects=Project.visible().order_by(Project.sort_order, Project.id).all())


# ------------------------------------------------------------------ 운영 중인 곳
def showcase_page(slug):
    item = Showcase.query.filter_by(slug=slug).first_or_404()
    series = Project.visible().filter(Project.title.contains("느린책방")).first() if slug == "rest" else None
    return render_template("showcase.html", item=item, videos=item.visible_videos, series=series)


@app.route("/rest")
def rest():
    return showcase_page("rest")


@app.route("/sofa")
def sofa():
    return showcase_page("sofa")


# ------------------------------------------------------------------ 검색·피드
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()[:80]
    projects_found, posts_found, books_found = [], [], []
    if q:
        like = f"%{q}%"
        projects_found = Project.visible().filter(search_filter(Project, q)).limit(10).all()
        posts_found = Archive.visible().filter(search_filter(Archive, q)).order_by(date_order().desc()).limit(30).all()
        books_found = Book.query.filter(or_(Book.title.ilike(like), Book.author.ilike(like))).limit(10).all()
    return render_template("search.html", q=q, projects=projects_found, posts=posts_found, books=books_found)


@app.route("/sitemap.xml")
def sitemap():
    pages = [url_for(name, _external=True) for name in ("home", "projects", "notes", "reading", "about", "rest", "sofa")]
    for project in Project.visible().all():
        pages.append(project_url(project, external=True))
    for post in Archive.visible().all():
        pages.append(post_url(post, external=True))
    for book in Book.query.all():
        pages.append(url_for("book_detail", book_id=book.id, _external=True))
    return Response(render_template("sitemap.xml", pages=pages), mimetype="application/xml")


@app.route("/rss.xml")
def rss():
    posts = Archive.visible().order_by(date_order().desc()).limit(30).all()
    items = [{"title": p.title, "link": post_url(p, external=True), "summary": p.summary or plain_excerpt(p.blocks, 300),
              "date": format_datetime(p.display_date) if p.display_date else "", "category": p.category} for p in posts]
    return Response(render_template("rss.xml", items=items), mimetype="application/rss+xml")


@app.route("/robots.txt")
def robots():
    body = f"User-agent: *\nDisallow: /admin\nSitemap: {url_for('sitemap', _external=True)}\n"
    return Response(body, mimetype="text/plain")


# ------------------------------------------------------------------ 예전 URL 연결
@app.route("/archive")
@app.route("/records")
def legacy_notes():
    return redirect(url_for("notes", **request.args), 301)


@app.route("/blog")
@app.route("/life")
def legacy_life():
    return redirect(url_for("notes", type="life", **{k: v for k, v in request.args.items() if k != "type"}), 301)


@app.route("/life/<key>")
@app.route("/reading/<key>")
def legacy_post_key(key):
    post = by_key(Archive.query, Archive, key) or abort(404)
    return redirect(post_url(post), 301)


@app.route("/archive/<int:post_id>")
@app.route("/blog/<int:post_id>")
@app.route("/records/<int:post_id>")
def legacy_post(post_id):
    post = Archive.query.get_or_404(post_id)
    return redirect(post_url(post), 301)


@app.route("/momoseul")
def legacy_momoseul():
    return redirect(url_for("rest"), 301)


@app.route("/records/new")
@app.route("/archive/new")
def legacy_new():
    return redirect(url_for("admin.write", kind="notes"))


@app.route("/records/<int:post_id>/edit")
def legacy_edit(post_id):
    post = Archive.query.get_or_404(post_id)
    return redirect(url_for("admin.write", kind=post.content_type, id=post.id))


@app.errorhandler(404)
def not_found(error):
    return render_template("errors.html", code=404, message="찾는 페이지가 없어요."), 404


@app.errorhandler(400)
def bad_request(error):
    return render_template("errors.html", code=400, message="요청을 처리하지 못했어요. 페이지를 새로고침한 뒤 다시 해 볼까요?"), 400


# ------------------------------------------------------------------ 명령어
@app.cli.command("seed")
def seed_command():
    """빈 DB일 때만 기본 데이터를 넣는다. 운영 DB에는 아무것도 하지 않는다."""
    from seed import seed_database

    click.echo("기본 데이터를 넣었습니다." if seed_database() else "이미 데이터가 있어 건너뜁니다.")


@app.cli.command("notion-sync")
@click.option("--full", is_flag=True, help="고친 시간과 상관없이 모두 다시 가져온다")
@click.option("--check", is_flag=True, help="연결과 속성만 확인한다")
def notion_sync_command(full, check):
    """노션 독서 DB → 사이트 한 방향 동기화."""
    import notion_sync
    from models import SyncLog

    token, db_value = app.config["NOTION_TOKEN"], app.config["NOTION_READING_DB"]
    if check:
        info = notion_sync.inspect(token, db_value)
        click.echo(f"DB: {info['title']}")
        for name, kind in info["properties"].items():
            field = next((f for f, n in info["mapping"].items() if n == name), "—")
            click.echo(f"  {name} ({kind}) → {field}")
        return
    log = SyncLog(source="notion")
    db.session.add(log)
    result = notion_sync.sync(token, db_value, full=full)
    log.status, log.created_count, log.updated_count = "success", result["created"], result["updated"]
    log.message, log.finished_at = result["message"], datetime.utcnow()
    db.session.commit()
    click.echo(f"신규 {result['created']} · 갱신 {result['updated']} · 그대로 {result['unchanged']} · 보류 제외 {result['held']} · 표지 {result['covers']}")
    click.echo(result["message"])


@app.cli.command("hash-password")
@click.option("--password", prompt="새 관리자 비밀번호", hide_input=True, confirmation_prompt=True)
def hash_password_command(password):
    """ADMIN_PASSWORD_HASH 값을 만든다."""
    click.echo(generate_password_hash(password))


if __name__ == "__main__":
    app.run(debug=True)
