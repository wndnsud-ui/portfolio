"""관리자: 로그인, 콘텐츠 관리(/admin), 글쓰기 스튜디오(/admin/write), 댓글, 가져오기."""
import json
from datetime import datetime, timedelta

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import func

from auth import admin_required, admin_return_url, check_credentials, clear_failures, client_ip, locked_seconds, login_admin, record_failure
from content import (BOOK_STATUS, CATEGORIES, KINDS, LIFE_CATEGORIES, NOTES_CATEGORIES, POST_KINDS, SINGLE_KINDS, TINTS,
                     clean_text, clean_url, normalize_blocks, normalize_design, slugify, social_url, youtube_id)
from models import Archive, Book, Experience, Profile, Project, RecordComment, Showcase, Skill, SyncLog, Video, db
import books_api
from storage import FILE_TYPES, UploadError, put_bytes, save_upload

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
KST = timedelta(hours=9)  # 공개 예약 시각은 한국 시간으로 입력·표시하고 DB에는 UTC로 저장한다


# ------------------------------------------------------------------ 로그인
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    ip = client_ip()
    if request.method == "POST":
        wait = locked_seconds(ip)
        if wait:
            flash(f"5번 틀려서 잠시 잠겼어요. {wait // 60 + 1}분 뒤에 다시 해 주세요.", "error")
        elif check_credentials(request.form.get("username", ""), request.form.get("password", "")):
            clear_failures(ip)
            login_admin()
            target = request.args.get("next", "")
            return redirect(admin_return_url(target), code=303)
        else:
            record_failure(ip)
            flash("아이디나 비밀번호가 맞지 않아요. 5번 틀리면 잠시 잠겨요.", "error")
    configured = bool(current_app.config.get("ADMIN_USERNAME") and current_app.config.get("ADMIN_PASSWORD_HASH"))
    return render_template("admin/login.html", configured=configured)


@admin_bp.post("/logout")
def logout():
    from flask import session

    session.clear()
    return redirect(url_for("home"))


# ------------------------------------------------------------------ 콘텐츠 관리
def edit_kind(item):
    """글쓰기 종류: 일상(life) 글도 「기록」에서 고친다."""
    return "reading" if item.content_type == "reading" else "notes"


def content_rows():
    rows = []
    for p in Project.query.all():
        rows.append({"kind": "project", "id": p.id, "title": p.title, "status": p.status, "scheduled": p.is_scheduled,
                     "updated": p.updated_at, "item": p})
    for a in Archive.query.all():
        rows.append({"kind": edit_kind(a), "id": a.id, "title": a.title, "status": a.status, "scheduled": a.is_scheduled,
                     "updated": a.updated_at, "item": a, "notion": a.source_type == "notion"})
    profile = Profile.query.first()
    if profile:
        rows.append({"kind": "about", "id": profile.id, "title": "소개 · 이력서", "status": "published",
                     "scheduled": False, "updated": profile.updated_at, "item": profile})
    rows.sort(key=lambda r: r["updated"] or datetime.min, reverse=True)
    return rows


@admin_bp.route("")
@admin_bp.route("/")
@admin_required
def dashboard():
    kind = request.args.get("kind", "")
    status = request.args.get("status", "")
    rows = content_rows()
    kind_counts = {k: sum(1 for r in rows if r["kind"] == k) for k in KINDS}
    if kind in KINDS:
        rows = [r for r in rows if r["kind"] == kind]
    if status in ("published", "draft"):
        rows = [r for r in rows if r["status"] == status]
    all_rows = content_rows()
    week_ago = datetime.utcnow() - timedelta(days=7)
    summary = {
        "published": sum(1 for r in all_rows if r["status"] == "published"),
        "draft": sum(1 for r in all_rows if r["status"] == "draft"),
        "comments": RecordComment.query.filter(RecordComment.created_at >= week_ago).count(),
        "synced": SyncLog.query.order_by(SyncLog.started_at.desc()).first(),
    }
    return render_template("admin/dashboard.html", rows=rows, kind=kind, status=status, kind_counts=kind_counts,
                           total=len(all_rows), summary=summary)


@admin_bp.post("/delete/<kind>/<int:item_id>")
@admin_required
def delete(kind, item_id):
    if kind == "project":
        item = Project.query.get_or_404(item_id)
    elif kind in POST_KINDS:
        item = Archive.query.get_or_404(item_id)
    elif kind == "notes":
        item = Archive.query.get_or_404(item_id)
    else:
        abort(404)
    db.session.delete(item)
    db.session.commit()
    flash(f"「{item.title}」을(를) 지웠어요.", "success")
    return redirect(url_for("admin.dashboard", kind=request.args.get("back_kind", "")))


# ------------------------------------------------------------------ 댓글
@admin_bp.route("/comments")
@admin_required
def comments():
    items = RecordComment.query.order_by(RecordComment.created_at.desc()).limit(300).all()
    return render_template("admin/comments.html", comments=items)


@admin_bp.post("/comments/<int:comment_id>/toggle")
@admin_required
def toggle_comment(comment_id):
    comment = RecordComment.query.get_or_404(comment_id)
    comment.is_hidden = not comment.is_hidden
    db.session.commit()
    return redirect(url_for("admin.comments"))


@admin_bp.post("/comments/<int:comment_id>/delete")
@admin_required
def delete_comment(comment_id):
    db.session.delete(RecordComment.query.get_or_404(comment_id))
    db.session.commit()
    flash("댓글을 지웠어요.", "success")
    return redirect(url_for("admin.comments"))


# ------------------------------------------------------------------ 가져오기 (노션 단계 0·1)
@admin_bp.route("/import", methods=["GET", "POST"])
@admin_required
def importer():
    if request.method == "POST":
        from import_reading_data import import_books, parse_upload

        upload = request.files.get("file")
        log = SyncLog(source="file")
        db.session.add(log)
        try:
            records = parse_upload(upload)
            created, updated, notes, skipped = import_books(records)
            log.status, log.created_count, log.updated_count = "success", created, updated
            log.message = f"{upload.filename}: 노트 {notes}개, 건너뜀 {skipped}개"
            flash(f"가져오기 완료 — 신규 도서 {created}, 갱신 {updated}, 노트 {notes}", "success")
        except Exception as error:  # 잘못된 파일이어도 기록은 남긴다
            db.session.rollback()
            log = SyncLog(source="file", status="failed", message=str(error)[:500])
            db.session.add(log)
            flash(f"가져오기 실패: {error}", "error")
        log.finished_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("admin.importer"))
    logs = SyncLog.query.order_by(SyncLog.started_at.desc()).limit(20).all()
    cfg = current_app.config
    notion_ready = bool(cfg.get("NOTION_TOKEN") and cfg.get("NOTION_READING_DB"))
    last_sync = SyncLog.query.filter_by(source="notion", status="success").order_by(SyncLog.started_at.desc()).first()
    return render_template("admin/import.html", logs=logs, books=Book.query.count(), notion_ready=notion_ready,
                           last_sync=last_sync)


@admin_bp.route("/import/notion", methods=["POST"])
@admin_required
def notion_import():
    import notion_sync

    token, db_value = current_app.config["NOTION_TOKEN"], current_app.config["NOTION_READING_DB"]
    full = request.form.get("full") == "1"
    log = SyncLog(source="notion")
    db.session.add(log)
    db.session.commit()
    try:
        result = notion_sync.sync(token, db_value, full=full)
        log.status, log.created_count, log.updated_count = "success", result["created"], result["updated"]
        log.message = result["message"]
        text = f"노션에서 가져왔어요 — 새 책 {result['created']}권, 고친 책 {result['updated']}권"
        if result["unchanged"]:
            text += f", 그대로 {result['unchanged']}권"
        if result["held"]:
            text += f", 보류라서 뺀 책 {result['held']}권"
        if result.get("removed"):
            text += f"(책장에서 내린 책 {result['removed']}권)"
        if result["covers"]:
            text += f". 표지 {result['covers']}장은 카카오 책 검색으로 채웠어요"
        flash(text + ".", "success")
    except Exception as error:  # 실패해도 기록은 남긴다
        db.session.rollback()
        log = db.session.merge(log)
        log.status, log.message = "failed", str(error)[:500]
        flash(f"가져오지 못했어요: {error}", "error")
    log.finished_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("admin.importer"))


# ------------------------------------------------------------------ 글쓰기 스튜디오
def to_kst_input(value):
    return (value + KST).strftime("%Y-%m-%dT%H:%M") if value else ""


def from_kst_input(value):
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M") - KST if value else None
    except ValueError:
        return None


def unique_slug(model, wanted, item_id):
    base = slugify(wanted) or None
    if not base:
        return None
    slug, n = base, 2
    while model.query.filter(model.slug == slug, model.id != (item_id or 0)).first():
        slug, n = f"{base}-{n}", n + 1
    return slug


def load_item(kind, item_id):
    if kind == "about":
        profile = Profile.query.first()
        if profile is None:
            profile = Profile()
            db.session.add(profile)
            db.session.flush()
        return profile
    if not item_id:
        return None
    if kind == "project":
        return Project.query.get_or_404(item_id)
    return Archive.query.filter_by(id=item_id).first_or_404()


PROJECT_FIELDS = ("category", "subtitle", "description", "role", "period", "tech_stack", "problem", "action", "process", "trouble",
                  "solution", "result", "insight", "demo_url", "github_url")
PROJECT_LIMITS = {"category": 80, "subtitle": 240, "period": 80, "tech_stack": 400}


def item_payload(kind, item):
    """스튜디오가 쓰는 초기 데이터(JSON)."""
    if kind == "about":
        p = item
        return {
            "kind": kind, "id": p.id, "title": p.name or "", "status": "published",
            "blocks": p.blocks or ([{"type": "paragraph", "text": p.intro}] if p.intro else []),
            "design": normalize_design(p.design, kind),
            "about": {
                "name": p.name or "", "headline": p.headline or "", "intro": p.intro or "", "email": p.email or "",
                "github": p.github or "", "notion": p.notion or "", "photo": p.photo or "", "resume_url": p.resume_url or "",
                "stats": [dict({"label": "", "value": "", "note": ""}, **s) for s in (p.stats or [])[:4]]
                         + [{"label": "", "value": "", "note": ""} for _ in range(max(0, 4 - len(p.stats or [])))],
                "tagline": p.get("tagline"), "home_lead": p.get("home_lead"), "summary": p.get("summary"),
                "seeking": bool((p.extra or {}).get("seeking", True)),
                "strengths": [dict({"title": "", "text": ""}, **x) for x in (p.get("strengths", []) or [])[:4]]
                             + [{"title": "", "text": ""} for _ in range(max(0, 4 - len(p.get("strengths", []) or [])))],
                "experiences": [{"id": e.id, "company": e.company or "", "position": e.position or "", "start_date": e.start_date or "",
                                 "end_date": e.end_date or "", "description": e.description or "", "achievement": e.achievement or "",
                                 "kind": e.kind or "work"}
                                for e in Experience.query.order_by(Experience.sort_order, Experience.id)],
                "skills": [{"id": s.id, "category": s.category, "name": s.name}
                           for s in Skill.query.order_by(Skill.category, Skill.sort_order)],
            },
        }
    if item is None:
        payload = {"kind": kind, "id": None, "title": "", "summary": "", "status": "draft", "category": "",
                   "tags": "", "slug": "", "is_pinned": False, "published_at": "", "cover_image": "",
                   "blocks": [{"type": "paragraph", "text": ""}], "design": normalize_design(None, kind)}
        if kind == "project":
            payload["project"] = {k: "" for k in PROJECT_FIELDS}
        if kind == "reading":
            payload["book"] = {"id": None, "title": "", "author": "", "publisher": "", "genre": "", "start_date": "", "finish_date": "",
                               "rating": 0, "cover_image": "", "status": "reading"}
        if kind in CATEGORIES:
            payload["category"] = CATEGORIES[kind][0]
        return payload
    payload = {"kind": kind, "id": item.id, "title": item.title, "status": item.status, "slug": item.slug or "",
               "published_at": to_kst_input(item.published_at) if item.is_scheduled else "",
               "cover_image": item.cover_image or item.thumbnail or "", "blocks": item.blocks or [],
               "design": normalize_design(item.design, kind)}
    if kind == "project":
        payload.update(summary=item.description or "", category="", tags=item.tech_stack or "", is_pinned=False)
        payload["project"] = {k: getattr(item, k) or "" for k in PROJECT_FIELDS}
    else:
        payload.update(summary=item.summary or "", category=item.category, tags=item.tags or "", is_pinned=item.is_pinned,
                       source_type=item.source_type or "")
        if kind == "reading":
            b = item.book
            payload["book"] = {"id": b.id if b else None, "title": b.title if b else "", "author": (b.author if b else "") or "",
                               "publisher": (b.publisher if b else "") or "", "genre": (b.genre if b else "") or "",
                               "start_date": (b.start_date if b else "") or "",
                               "finish_date": (b.finish_date if b else "") or "", "rating": (b.rating if b else 0) or 0,
                               "cover_image": (b.cover_image if b else "") or "", "status": (b.status if b else "reading") or "reading"}
    return payload


def apply_about(profile, data):
    about = data.get("about") or {}
    for field in ("name", "headline", "email", "github", "notion"):
        setattr(profile, field, clean_text(about.get(field), 240))
    profile.name = profile.name or "최혜영"
    profile.headline = profile.headline or "복잡한 일을 잘 ==정리된 구조==로 바꾸는 사람입니다."
    profile.intro = clean_text(about.get("intro"), 2000)
    profile.photo = clean_url(about.get("photo")) or None
    profile.resume_url = clean_url(about.get("resume_url")) or None
    profile.blocks = normalize_blocks(data.get("blocks"))
    profile.design = normalize_design(data.get("design"), "about")
    profile.stats = [{"label": clean_text(s.get("label"), 40), "value": clean_text(s.get("value"), 20),
                      "note": clean_text(s.get("note"), 80)}
                     for s in (about.get("stats") or [])[:4] if isinstance(s, dict) and clean_text(s.get("value"), 20)]
    profile.extra = {
        **dict(profile.extra or {}),
        "tagline": clean_text(about.get("tagline"), 120), "home_lead": clean_text(about.get("home_lead"), 400),
        "summary": clean_text(about.get("summary"), 600), "seeking": bool(about.get("seeking")),
        "strengths": [{"title": clean_text(x.get("title"), 40), "text": clean_text(x.get("text"), 160)}
                      for x in (about.get("strengths") or [])[:4] if isinstance(x, dict) and clean_text(x.get("title"), 40)],
    }
    # 경력: 화면의 순서대로 sort_order를 다시 매기고, 목록에서 빠진 항목은 지운다
    keep = set()
    for order, row in enumerate(about.get("experiences") or [], start=1):
        if not isinstance(row, dict) or not clean_text(row.get("company"), 160):
            continue
        exp = Experience.query.get(row.get("id")) if str(row.get("id") or "").isdigit() else None
        exp = exp or Experience(company="")
        for field, limit in (("company", 160), ("position", 160), ("start_date", 40), ("end_date", 40),
                             ("description", 2000), ("achievement", 2000)):
            setattr(exp, field, clean_text(row.get(field), limit))
        exp.kind = "edu" if row.get("kind") == "edu" else "work"
        exp.sort_order = order
        db.session.add(exp)
        db.session.flush()
        keep.add(exp.id)
    for exp in Experience.query.all():
        if exp.id not in keep:
            db.session.delete(exp)
    keep = set()
    for order, row in enumerate(about.get("skills") or []):
        if not isinstance(row, dict) or not clean_text(row.get("name"), 120):
            continue
        skill = Skill.query.get(row.get("id")) if str(row.get("id") or "").isdigit() else None
        skill = skill or Skill(name="", category="")
        skill.name = clean_text(row.get("name"), 120)
        skill.category = clean_text(row.get("category"), 80).upper() or "WORK"
        skill.sort_order = order
        db.session.add(skill)
        db.session.flush()
        keep.add(skill.id)
    for skill in Skill.query.all():
        if skill.id not in keep:
            db.session.delete(skill)
    return profile


@admin_bp.route("/chatgpt", methods=["GET", "POST"])
@admin_required
def chatgpt():
    from chatgpt_bridge import manage
    response = current_app.make_response(manage())
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def apply_payload(kind, item, data, action):
    """스튜디오 입력을 검증해 저장한다. action: draft / publish / autosave"""
    if kind == "about":
        return apply_about(item, data)
    title = clean_text(data.get("title"), 200) or "제목 없음"
    if item is None:
        item = Project(title=title) if kind == "project" else Archive(title=title, category="", content_type="notes")
        db.session.add(item)
    item.title = title
    item.blocks = normalize_blocks(data.get("blocks"))
    item.design = normalize_design(data.get("design"), kind)
    item.cover_image = clean_url(data.get("cover_image")) or None
    model = Project if kind == "project" else Archive
    db.session.flush()
    item.slug = unique_slug(model, data.get("slug") or title, item.id)

    if action == "publish":
        scheduled = from_kst_input(data.get("published_at", ""))
        item.status = "published"
        item.published_at = scheduled or (item.published_at if item.published_at and item.published_at <= datetime.utcnow() else datetime.utcnow())
    elif action == "draft":
        item.status = "draft"

    if kind == "project":
        project = data.get("project") or {}
        for field in PROJECT_FIELDS:
            if field not in ("demo_url", "github_url"):
                setattr(item, field, clean_text(project.get(field), PROJECT_LIMITS.get(field, 4000)))
        item.demo_url = clean_url(project.get("demo_url"))
        item.github_url = clean_url(project.get("github_url"))
        return item

    item.summary = clean_text(data.get("summary"), 600)
    item.tags = ", ".join(t.strip().lstrip("#") for t in clean_text(data.get("tags"), 400).split(",") if t.strip())
    item.is_pinned = bool(data.get("is_pinned"))
    category = clean_text(data.get("category"), 80)
    if kind == "reading":
        item.content_type, item.category = "reading", "독서 노트"
    else:  # 기록: 분류가 일상 쪽이면 life, 아니면 notes
        item.content_type = "life" if category in LIFE_CATEGORIES else "notes"
        item.category = category if category in NOTES_CATEGORIES + LIFE_CATEGORIES else NOTES_CATEGORIES[0]
    if kind == "reading":
        book_data = data.get("book") or {}
        book = Book.query.get(book_data.get("id")) if str(book_data.get("id") or "").isdigit() else None
        book_title = clean_text(book_data.get("title"), 240)
        if book is None and book_title:
            book = Book(title=book_title)
            db.session.add(book)
        if book is not None:
            book.title = book_title or book.title
            for field, limit in (("author", 160), ("publisher", 160), ("genre", 120), ("start_date", 40), ("finish_date", 40)):
                setattr(book, field, clean_text(book_data.get(field), limit) or None)
            book.cover_image = clean_url(book_data.get("cover_image")) or None
            book.status = book_data.get("status") if book_data.get("status") in BOOK_STATUS else "reading"
            try:
                book.rating = max(0.0, min(5.0, float(book_data.get("rating") or 0))) or None
            except (TypeError, ValueError):
                book.rating = None
            db.session.flush()
            item.book_id = book.id
    return item


@admin_bp.route("/write", methods=["GET", "POST"])
@admin_required
def write():
    kind = request.values.get("kind", "notes")
    kind = "notes" if kind == "life" else kind
    if kind not in KINDS:
        abort(404)
    item_id = request.values.get("id", type=int)
    item = load_item(kind, item_id)
    if item is not None and kind in POST_KINDS + ("notes",) and edit_kind(item) != kind:
        return redirect(url_for("admin.write", kind=edit_kind(item), id=item.id))
    writing_step = request.values.get("step", "details" if item is None else "content")
    if writing_step not in ("details", "content", "media", "publish"):
        writing_step = "details"
    if request.method == "POST":
        action = request.form.get("action", "draft")
        try:
            data = json.loads(request.form.get("payload", "{}"))
        except ValueError:
            abort(400)
        item = apply_payload(kind, item, data, action)
        db.session.commit()
        if kind == "about":
            flash("소개 페이지를 저장했어요.", "success")
        elif action == "publish":
            flash("공개 예약했어요." if item.is_scheduled else "공개했어요.", "success")
        else:
            flash("임시저장했어요. 방문자에게는 아직 안 보여요.", "success")
        return redirect(url_for("admin.write", kind=kind, id=item.id, step=writing_step))
    if kind in SINGLE_KINDS:
        db.session.commit()
    books = Book.query.order_by(Book.title).all() if kind == "reading" else []
    books_json = [{"id": b.id, "title": b.title, "author": b.author or "", "publisher": b.publisher or "",
                   "genre": b.genre or "", "start_date": b.start_date or "", "finish_date": b.finish_date or "",
                   "rating": b.rating or 0, "cover_image": b.cover_image or "", "status": b.status or "reading",
                   "notion": bool(b.notion_page_id)} for b in books]
    notion_ready = bool(current_app.config.get("NOTION_TOKEN"))
    return render_template("admin/studio.html", kind=kind, item=item, payload=item_payload(kind, item), books=books_json, notion_ready=notion_ready,
                           note_categories=NOTES_CATEGORIES, life_categories=LIFE_CATEGORIES, writing_step=writing_step)


@admin_bp.post("/api/autosave")
@admin_required
def autosave():
    data = request.get_json(silent=True) or {}
    kind = data.get("kind")
    if kind not in KINDS or kind in SINGLE_KINDS:
        return jsonify(ok=False, error="unsupported"), 400
    item = load_item(kind, data.get("id") if str(data.get("id") or "").isdigit() else None)
    if item is not None and item.status == "published":
        # 공개 중인 글은 자동 저장으로 바로 바뀌면 안 된다. 브라우저에만 보관한다.
        return jsonify(ok=False, error="published"), 409
    item = apply_payload(kind, item, data, "autosave")
    item.status = "draft"
    db.session.commit()
    return jsonify(ok=True, id=item.id, slug=item.slug, saved_at=(datetime.utcnow() + KST).strftime("%H:%M:%S"),
                   edit_url=url_for("admin.write", kind=kind, id=item.id))


@admin_bp.post("/api/upload")
@admin_required
def upload():
    allowed = FILE_TYPES if request.form.get("type") == "file" else None
    try:
        url = save_upload(request.files.get("file"), **({"allowed": allowed} if allowed else {}))
    except UploadError as error:
        return jsonify(ok=False, error=str(error)), 400
    except Exception as error:  # 저장소 연결 오류 등
        current_app.logger.exception("upload failed")
        return jsonify(ok=False, error=f"업로드 실패: {error}"), 500
    if not url:
        return jsonify(ok=False, error="파일이 없습니다."), 400
    return jsonify(ok=True, url=url)


@admin_bp.get("/api/books/search")
@admin_required
def book_search():
    try:
        results = books_api.search(current_app.config.get("KAKAO_REST_API_KEY"), request.args.get("q", ""))
    except books_api.BookSearchError as error:
        return jsonify(ok=False, error=str(error)), 400
    return jsonify(ok=True, results=results)


@admin_bp.get("/api/notion/pages")
@admin_required
def notion_pages():
    """글쓰기 화면의 「노션」: 책(또는 붙여 넣은 노션 주소)의 페이지·하위 페이지 목록."""
    import notion_sync

    token = current_app.config.get("NOTION_TOKEN")
    if not token:
        return jsonify(ok=False, error="노션 키(NOTION_TOKEN)가 없어요."), 400
    root = ""
    if str(request.args.get("book_id", "")).isdigit():
        book = db.session.get(Book, int(request.args["book_id"]))
        root = (book.notion_page_id or "") if book else ""
    root = root or notion_sync.database_id(request.args.get("url", ""))
    if not root:
        return jsonify(ok=False, error="노션 페이지 주소를 붙여 넣어 주세요."), 400
    try:
        return jsonify(ok=True, pages=notion_sync.page_tree(token, root))
    except notion_sync.NotionError as error:
        return jsonify(ok=False, error=str(error)), 400


@admin_bp.get("/api/notion/blocks")
@admin_required
def notion_blocks():
    import notion_sync

    token = current_app.config.get("NOTION_TOKEN")
    page_id = notion_sync.database_id(request.args.get("page", ""))
    if not token or not page_id:
        return jsonify(ok=False, error="불러올 페이지가 없어요."), 400
    try:
        return jsonify(ok=True, **notion_sync.page_blocks(token, page_id))
    except notion_sync.NotionError as error:
        return jsonify(ok=False, error=str(error)), 400


@admin_bp.post("/api/books/cover")
@admin_required
def book_cover():
    """카카오 표지를 받아 우리 저장소에 올린다. 실패하면 썸네일 주소를 그대로 쓰도록 알려 준다."""
    candidates = [u for u in ((request.get_json(silent=True) or {}).get("urls") or []) if isinstance(u, str)][:2]
    error = "표지 주소가 없습니다."
    for url in candidates:
        try:
            data, extension = books_api.download_cover(url)
            return jsonify(ok=True, url=put_bytes(data, extension, folder="covers"))
        except books_api.BookSearchError as exc:
            error = str(exc)
        except Exception as exc:  # 저장소 연결 오류 등
            current_app.logger.exception("cover upload failed")
            error = f"표지 저장 실패: {exc}"
    return jsonify(ok=False, error=error), 400



# ------------------------------------------------------------------ 운영 중인 곳 · 영상 관리
YOUTUBE_HOSTS = ["youtube.com", "youtu.be"]


@admin_bp.route("/showcases")
@admin_required
def showcases():
    items = Showcase.query.order_by(Showcase.sort_order, Showcase.id).all()
    return render_template("admin/showcases.html", items=items, current=request.args.get("s") or (items[0].slug if items else ""))


@admin_bp.post("/showcases/<slug>")
@admin_required
def save_showcase(slug):
    item = Showcase.query.filter_by(slug=slug).first_or_404()
    f = request.form
    item.title = clean_text(f.get("title"), 120) or item.title
    item.status = "live" if f.get("status") == "live" else "soon"
    item.intro = clean_text(f.get("intro"), 1000)
    item.site_url = clean_url(f.get("site_url")) or None
    item.channel_url = social_url(f.get("channel_url"), YOUTUBE_HOSTS) or None
    item.launch_date = clean_text(f.get("launch_date"), 40) or None
    item.tint = f.get("tint") if f.get("tint") in TINTS else item.tint
    item.cards = [{"title": clean_text(f.get(f"card_title_{i}"), 40), "text": clean_text(f.get(f"card_text_{i}"), 400)}
                  for i in range(3)]
    extra = dict(item.extra or {})
    extra["label"] = clean_text(f.get("label"), 40)
    extra["summary"] = clean_text(f.get("summary"), 160)
    if slug == "rest":
        extra["items"] = [{"name": clean_text(f.get(f"item_{i}"), 40)} for i in range(4)]
    else:
        extra["hosts"] = [{"name": clean_text(f.get(f"host_name_{i}"), 40), "bio": clean_text(f.get(f"host_bio_{i}"), 120)}
                          for i in range(4)]
    item.extra = extra
    db.session.commit()
    flash(f"「{item.title}」을(를) 저장했어요.", "success")
    return redirect(url_for("admin.showcases", s=slug))


@admin_bp.post("/showcases/<slug>/videos")
@admin_required
def add_video(slug):
    item = Showcase.query.filter_by(slug=slug).first_or_404()
    video_id = youtube_id(request.form.get("url"))
    if not video_id:
        flash("유튜브 주소를 알아보지 못했어요. watch?v= · youtu.be/ · shorts/ 주소를 붙여 넣어 주세요.", "error")
        return redirect(url_for("admin.showcases", s=slug) + "#videos")
    last = max([v.sort_order for v in item.videos] or [0])
    episode = request.form.get("episode_no", type=int)
    if slug == "sofa" and not episode:
        episode = max([v.episode_no or 0 for v in item.videos] or [0]) + 1
    db.session.add(Video(showcase_id=item.id, youtube_id=video_id, sort_order=last + 1, episode_no=episode,
                         title=clean_text(request.form.get("title"), 200) or "제목을 적어 주세요",
                         published_at=clean_text(request.form.get("published_at"), 40) or None,
                         duration=clean_text(request.form.get("duration"), 20) or None))
    db.session.commit()
    flash("영상을 추가했어요. 제목·날짜·길이를 확인해 주세요.", "success")
    return redirect(url_for("admin.showcases", s=slug) + "#videos")


@admin_bp.post("/videos/<int:video_id>")
@admin_required
def update_video(video_id):
    video = Video.query.get_or_404(video_id)
    slug = video.showcase.slug
    action = request.form.get("action", "save")
    siblings = list(video.showcase.videos)
    if action == "delete":
        db.session.delete(video)
        flash("영상을 지웠어요.", "success")
    elif action in ("up", "down"):
        index = siblings.index(video)
        target = index - 1 if action == "up" else index + 1
        if 0 <= target < len(siblings):
            siblings.insert(target, siblings.pop(index))
            for order, v in enumerate(siblings, start=1):
                v.sort_order = order
    elif action == "toggle":
        video.is_visible = not video.is_visible
    else:
        video.title = clean_text(request.form.get("title"), 200) or video.title
        video.published_at = clean_text(request.form.get("published_at"), 40) or None
        video.duration = clean_text(request.form.get("duration"), 20) or None
        video.episode_no = request.form.get("episode_no", type=int)
        new_id = youtube_id(request.form.get("url"))
        if new_id:
            video.youtube_id = new_id
        flash("영상 정보를 저장했어요.", "success")
    db.session.commit()
    return redirect(url_for("admin.showcases", s=slug) + "#videos")
